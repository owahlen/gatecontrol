package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"gatecontrol/internal/app"
	"gatecontrol/internal/config"
	"gatecontrol/internal/dido"
	"gatecontrol/internal/domain"
	"gatecontrol/internal/mocks"
	mqttadapter "gatecontrol/internal/mqtt"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "config error: %v\n", err)
		os.Exit(1)
	}

	logger := newLogger(cfg.LogLevel)

	var hardware domain.GateHardware
	if cfg.UseMockDIDO {
		hardware = mocks.NewMockDIDO(cfg.PulseLength)
		logger.Info("using mock DIDO hardware")
	} else {
		hardware, err = dido.Open(dido.Config{
			Bus:          cfg.SPIBus,
			ChipSelect:   cfg.SPIChipSelect,
			HardwareAddr: cfg.SPIHardwareAddr,
			RelayPin:     cfg.DIDORelayPin,
			SpeedHz:      cfg.SPISpeedHz,
			PulseLength:  cfg.PulseLength,
		})
		if err != nil {
			fmt.Fprintf(os.Stderr, "dido init error: %v\n", err)
			os.Exit(1)
		}
		logger.Info(
			"using DIDO SPI hardware",
			"bus", cfg.SPIBus,
			"chip_select", cfg.SPIChipSelect,
			"hardware_addr", cfg.SPIHardwareAddr,
			"relay_pin", cfg.DIDORelayPin,
			"speed_hz", cfg.SPISpeedHz,
		)
	}

	var commandSub domain.CommandSubscriber
	var statePub domain.StatePublisher
	if cfg.UseMockMQTT {
		mock := mocks.NewMockMQTT()
		commandSub = mock
		statePub = mock
		logger.Info("using mock MQTT adapter")
	} else {
		brokerURL := fmt.Sprintf("tcp://%s:%d", cfg.MQTTBroker, cfg.MQTTPort)
		client, err := mqttadapter.New(mqttadapter.Config{
			BrokerURL: brokerURL,
			ClientID:  cfg.MQTTClientID,
			Username:  cfg.MQTTUsername,
			Password:  cfg.MQTTPassword,
			BaseTopic: cfg.MQTTBase,
		}, logger)
		if err != nil {
			fmt.Fprintf(os.Stderr, "mqtt init error: %v\n", err)
			os.Exit(1)
		}

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		if err := client.Connect(ctx); err != nil {
			cancel()
			fmt.Fprintf(os.Stderr, "mqtt connect error: %v\n", err)
			os.Exit(1)
		}
		cancel()

		commandSub = client
		statePub = client
	}

	svc := app.NewService(hardware, commandSub, statePub, logger, cfg.InitialState)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := svc.Run(ctx); err != nil {
		logger.Error("service exited with error", "err", err)
		os.Exit(1)
	}
}

func newLogger(level string) *slog.Logger {
	var l slog.Level
	switch level {
	case "debug":
		l = slog.LevelDebug
	case "warn":
		l = slog.LevelWarn
	case "error":
		l = slog.LevelError
	default:
		l = slog.LevelInfo
	}
	h := slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: l})
	return slog.New(h)
}
