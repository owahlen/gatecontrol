package mqtt

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"sync"
	"time"

	"gatecontrol/internal/domain"

	paho "github.com/eclipse/paho.mqtt.golang"
)

// Client is the concrete MQTT adapter implementing:
//   - domain.CommandSubscriber
//   - domain.StatePublisher
//
// It receives commands on `<base>/command` and publishes:
//   - `<base>/state`
//   - `<base>/target_state`
//   - `<base>/availability`
type Client struct {
	baseTopic string
	command   string
	state     string
	target    string
	avail     string

	logger *slog.Logger
	client paho.Client

	handlerMu sync.RWMutex
	handler   func(domain.Command) error
}

// Config contains connection and topic settings for MQTT.
type Config struct {
	// BrokerURL example: tcp://localhost:1883
	BrokerURL string
	// ClientID should be unique per running gateway process.
	ClientID string
	// Username/Password are optional for authenticated brokers.
	Username string
	Password string
	// BaseTopic defaults to "faac/gate" when empty.
	BaseTopic string
}

// New creates an MQTT adapter but does not connect yet.
func New(cfg Config, logger *slog.Logger) (*Client, error) {
	if logger == nil {
		logger = slog.Default()
	}
	if strings.TrimSpace(cfg.BrokerURL) == "" {
		return nil, fmt.Errorf("broker URL is required")
	}
	base := strings.Trim(strings.TrimSpace(cfg.BaseTopic), "/")
	if base == "" {
		base = "faac/gate"
	}

	c := &Client{
		baseTopic: base,
		command:   fmt.Sprintf("%s/command", base),
		state:     fmt.Sprintf("%s/state", base),
		target:    fmt.Sprintf("%s/target_state", base),
		avail:     fmt.Sprintf("%s/availability", base),
		logger:    logger,
	}

	opts := paho.NewClientOptions()
	opts.AddBroker(cfg.BrokerURL)
	opts.SetClientID(cfg.ClientID)
	opts.SetAutoReconnect(true)
	opts.SetConnectRetry(true)
	opts.SetConnectRetryInterval(2 * time.Second)
	opts.SetOrderMatters(false)
	opts.SetCleanSession(false)
	opts.SetWill(c.avail, "offline", 1, true)

	if cfg.Username != "" {
		opts.SetUsername(cfg.Username)
		opts.SetPassword(cfg.Password)
	}

	opts.OnConnect = func(cl paho.Client) {
		if token := cl.Subscribe(c.command, 1, c.onMessage); token.Wait() && token.Error() != nil {
			c.logger.Error("mqtt subscribe failed", "topic", c.command, "err", token.Error())
			return
		}
		c.logger.Info("mqtt connected", "command_topic", c.command)
	}

	opts.OnConnectionLost = func(_ paho.Client, err error) {
		c.logger.Warn("mqtt connection lost", "err", err)
	}

	c.client = paho.NewClient(opts)
	return c, nil
}

// Connect establishes a broker connection within the context deadline.
func (c *Client) Connect(ctx context.Context) error {
	token := c.client.Connect()
	if !token.WaitTimeout(waitFromContext(ctx, 10*time.Second)) {
		return fmt.Errorf("mqtt connect timeout")
	}
	if err := token.Error(); err != nil {
		return fmt.Errorf("mqtt connect: %w", err)
	}
	return nil
}

// SubscribeCommands stores the callback used by incoming MQTT messages.
//
// Actual MQTT topic subscription is configured in OnConnect so reconnects
// automatically re-subscribe.
func (c *Client) SubscribeCommands(_ context.Context, handler func(domain.Command) error) error {
	c.handlerMu.Lock()
	defer c.handlerMu.Unlock()
	c.handler = handler
	return nil
}

// PublishState publishes retained state (OPEN/CLOSED/OPENING/CLOSING/STOPPED).
func (c *Client) PublishState(ctx context.Context, state domain.GateState) error {
	token := c.client.Publish(c.state, 1, true, string(state))
	if !token.WaitTimeout(waitFromContext(ctx, 5*time.Second)) {
		return fmt.Errorf("mqtt publish state timeout")
	}
	if err := token.Error(); err != nil {
		return fmt.Errorf("mqtt publish state: %w", err)
	}
	return nil
}

// PublishTargetState publishes retained target command ("open" or "close").
func (c *Client) PublishTargetState(ctx context.Context, target domain.Command) error {
	token := c.client.Publish(c.target, 1, true, string(target))
	if !token.WaitTimeout(waitFromContext(ctx, 5*time.Second)) {
		return fmt.Errorf("mqtt publish target_state timeout")
	}
	if err := token.Error(); err != nil {
		return fmt.Errorf("mqtt publish target_state: %w", err)
	}
	return nil
}

// PublishAvailability publishes retained availability ("online"/"offline").
func (c *Client) PublishAvailability(ctx context.Context, online bool) error {
	payload := "offline"
	if online {
		payload = "online"
	}
	token := c.client.Publish(c.avail, 1, true, payload)
	if !token.WaitTimeout(waitFromContext(ctx, 5*time.Second)) {
		return fmt.Errorf("mqtt publish availability timeout")
	}
	if err := token.Error(); err != nil {
		return fmt.Errorf("mqtt publish availability: %w", err)
	}
	return nil
}

// Close disconnects from broker and flushes inflight messages briefly.
func (c *Client) Close() error {
	if c.client != nil && c.client.IsConnectionOpen() {
		c.client.Disconnect(250)
	}
	return nil
}

// onMessage handles command topic payloads.
//
// Invalid command strings are ignored with a warning.
func (c *Client) onMessage(_ paho.Client, m paho.Message) {
	cmd, ok := domain.NormalizeCommand(string(m.Payload()))
	if !ok {
		c.logger.Warn("ignored invalid mqtt command", "payload", string(m.Payload()))
		return
	}

	c.handlerMu.RLock()
	h := c.handler
	c.handlerMu.RUnlock()
	if h == nil {
		return
	}
	if err := h(cmd); err != nil {
		c.logger.Warn("command handler error", "cmd", cmd, "err", err)
	}
}

// waitFromContext derives a timeout for MQTT token waits.
//
// If the context has a deadline, that remaining duration is used.
// Otherwise fallback is returned.
func waitFromContext(ctx context.Context, fallback time.Duration) time.Duration {
	if dl, ok := ctx.Deadline(); ok {
		remaining := time.Until(dl)
		if remaining <= 0 {
			return 0
		}
		return remaining
	}
	return fallback
}
