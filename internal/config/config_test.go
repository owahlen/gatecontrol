package config

import (
	"testing"
	"time"

	"gatecontrol/internal/domain"
)

func TestLoadDefaults(t *testing.T) {
	t.Setenv("MQTT_BROKER", "")
	t.Setenv("MQTT_PORT", "")
	t.Setenv("MQTT_CLIENT_ID", "")
	t.Setenv("MQTT_USERNAME", "")
	t.Setenv("MQTT_PASSWORD", "")
	t.Setenv("MQTT_BASE_TOPIC", "")
	t.Setenv("USE_MOCK_MQTT", "")
	t.Setenv("SPI_BUS", "")
	t.Setenv("SPI_CHIP_SELECT", "")
	t.Setenv("SPI_HARDWARE_ADDR", "")
	t.Setenv("DIDO_RELAY_PIN", "")
	t.Setenv("SPI_SPEED_HZ", "")
	t.Setenv("PULSE_LENGTH_MS", "")
	t.Setenv("USE_MOCK_DIDO", "")
	t.Setenv("LOG_LEVEL", "")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("load defaults: %v", err)
	}

	if cfg.MQTTBroker != "localhost" {
		t.Fatalf("MQTTBroker=%q", cfg.MQTTBroker)
	}
	if cfg.MQTTPort != 1883 {
		t.Fatalf("MQTTPort=%d", cfg.MQTTPort)
	}
	if cfg.MQTTClientID != "gatecontrol" {
		t.Fatalf("MQTTClientID=%q", cfg.MQTTClientID)
	}
	if cfg.MQTTBase != "faac/gate" {
		t.Fatalf("MQTTBase=%q", cfg.MQTTBase)
	}
	if cfg.SPIBus != 0 || cfg.SPIChipSelect != 0 || cfg.SPIHardwareAddr != 0 || cfg.DIDORelayPin != 0 {
		t.Fatalf("unexpected spi defaults: %+v", cfg)
	}
	if cfg.SPISpeedHz != 100000 {
		t.Fatalf("SPISpeedHz=%d", cfg.SPISpeedHz)
	}
	if cfg.PulseLength != 500*time.Millisecond {
		t.Fatalf("PulseLength=%s", cfg.PulseLength)
	}
	if cfg.InitialState != domain.StateClosed {
		t.Fatalf("InitialState=%s", cfg.InitialState)
	}
}

func TestLoadFromEnvironment(t *testing.T) {
	t.Setenv("MQTT_BROKER", "broker")
	t.Setenv("MQTT_PORT", "1884")
	t.Setenv("MQTT_CLIENT_ID", "client")
	t.Setenv("MQTT_USERNAME", "user")
	t.Setenv("MQTT_PASSWORD", "pass")
	t.Setenv("MQTT_BASE_TOPIC", "test/gate")
	t.Setenv("USE_MOCK_MQTT", "true")
	t.Setenv("SPI_BUS", "1")
	t.Setenv("SPI_CHIP_SELECT", "2")
	t.Setenv("SPI_HARDWARE_ADDR", "3")
	t.Setenv("DIDO_RELAY_PIN", "4")
	t.Setenv("SPI_SPEED_HZ", "200000")
	t.Setenv("PULSE_LENGTH_MS", "25")
	t.Setenv("USE_MOCK_DIDO", "true")
	t.Setenv("LOG_LEVEL", "debug")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("load env: %v", err)
	}

	if cfg.MQTTBroker != "broker" || cfg.MQTTPort != 1884 || cfg.MQTTClientID != "client" {
		t.Fatalf("unexpected mqtt config: %+v", cfg)
	}
	if cfg.MQTTUsername != "user" || cfg.MQTTPassword != "pass" || cfg.MQTTBase != "test/gate" {
		t.Fatalf("unexpected mqtt credentials/topic: %+v", cfg)
	}
	if !cfg.UseMockMQTT || !cfg.UseMockDIDO {
		t.Fatalf("expected mock flags true: %+v", cfg)
	}
	if cfg.SPIBus != 1 || cfg.SPIChipSelect != 2 || cfg.SPIHardwareAddr != 3 || cfg.DIDORelayPin != 4 {
		t.Fatalf("unexpected spi config: %+v", cfg)
	}
	if cfg.SPISpeedHz != 200000 || cfg.PulseLength != 25*time.Millisecond || cfg.LogLevel != "debug" {
		t.Fatalf("unexpected misc config: %+v", cfg)
	}
}
