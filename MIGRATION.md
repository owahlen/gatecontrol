# Migration Plan: Python/REST DIDO to Go/MQTT DIDO

This document outlines the work needed to replace the current Python implementation in
`gatecontrol` with the Go/MQTT implementation from `gatecontrol2`, while keeping the
working DIDO board relay control instead of using the USB FAAC protocol.

## Current State

### `gatecontrol`

`gatecontrol` currently contains a Python FastAPI service:

- REST endpoints receive open/close requests.
- `GateService` translates requests into a relay pulse.
- `DidoSpiRelayHardware` talks to the DIDO board over SPI.
- State is reported back to Homebridge through HTTP webhooks.
- The latest DIDO backend no longer depends on `piface`; it directly writes to an
  MCP23S17-style SPI GPIO expander using `spidev`.
- The current DIDO mode only controls `Relay0`; it does not read gate status inputs.
  Because of that, the service keeps an assumed state in memory after a command.

Important existing Python behavior to preserve:

- Pulse `IN 1` by setting the relay active for `0.5s`, then inactive, then wait another
  `0.5s`.
- Avoid pulsing if the assumed state already equals the requested target.
- Default DIDO settings:
  - `SPI_BUS=0`
  - `SPI_CHIP_SELECT=0`
  - `SPI_HARDWARE_ADDR=0`
  - `DIDO_RELAY_PIN=0`
- MCP23S17 writes:
  - `IOCON` register `0x0A`
  - `IODIRA` register `0x00`
  - `GPIOA` register `0x12`
  - control byte `0x40 | ((hardware_addr << 1) & 0x0E) | rw_bit`
  - write frames are `[control, register, data]`

### `gatecontrol2`

`gatecontrol2` contains the desired Go/MQTT shape:

- Go application entrypoint in `cmd/gatecontrol2/main.go`.
- MQTT command subscriber and state publisher in `internal/mqtt`.
- Domain types for commands and states in `internal/domain`.
- Testable architecture using ports/interfaces and mocks.
- Cross-compilation documentation for Raspberry Pi Zero/Zero W ARMv6.

However, its gate control path is USB-specific:

- `internal/usb` sends reverse-engineered FAAC serial frames.
- `internal/app.Service` periodically polls the USB transport for position frames.
- State is derived from USB-reported wing positions.

This USB protocol must not be used for this migration.

## Target Architecture

The migrated `gatecontrol` should be a Go service with these responsibilities:

- Subscribe to MQTT commands:
  - `<base>/command` payload `open`
  - `<base>/command` payload `close`
- Publish MQTT state:
  - `<base>/state`
  - `<base>/target_state`
  - `<base>/availability`
- Control the existing DIDO board over SPI.
- Keep the old assumed-state behavior until input feedback is implemented.
- Build as a static Go binary for Raspberry Pi Zero/Zero W.

Recommended package layout:

```text
cmd/gatecontrol/main.go
internal/app/service.go
internal/config/config.go
internal/domain/types.go
internal/domain/ports.go
internal/dido/spi_relay.go
internal/mqtt/client.go
internal/mocks/dido.go
internal/mocks/mqtt.go
```

The important change from `gatecontrol2` is the hardware boundary. Replace the
USB-oriented `GateTransport` abstraction with a DIDO-oriented interface, for example:

```go
type GateHardware interface {
    Pulse(ctx context.Context) error
    Close() error
}
```

If input feedback is added later, extend this deliberately instead of carrying over the
USB poll/read model:

```go
type GateFeedback interface {
    ReadOpen(ctx context.Context) (bool, error)
    ReadClosed(ctx context.Context) (bool, error)
}
```

## Migration Steps

1. Remove Python runtime files from `gatecontrol`.

   Delete or replace:

   - `app/`
   - `requirements.txt`
   - Python-specific test setup
   - FastAPI/REST documentation
   - Basic Auth and webhook configuration references

2. Copy the reusable Go structure from `gatecontrol2`.

   Bring over and rename:

   - `go.mod` and `go.sum`
   - `cmd/gatecontrol2/main.go` to `cmd/gatecontrol/main.go`
   - `internal/config`
   - `internal/mqtt`
   - `internal/domain/types.go`
   - `internal/domain/ports.go`, after changing the hardware interfaces
   - `internal/app`, after replacing USB poll logic with DIDO pulse logic
   - `internal/mocks`
   - Go tests, adapted to the new assumed-state behavior

3. Remove the USB protocol implementation.

   Do not migrate these files into the final service:

   - `internal/usb/serial_transport.go`
   - `internal/usb/serial_transport_unsupported.go`
   - USB command frame constants
   - USB poll frame constants
   - position response parser
   - `DetermineState` logic based on wing positions

   The FAAC USB code was valuable for `gatecontrol2`, but it is the wrong hardware path
   for this device.

4. Implement Go DIDO/SPI relay control.

   Create a Linux DIDO adapter that mirrors the current Python `DidoSpiRelayHardware`.

   Required behavior:

   - Open `/dev/spidev<SPI_BUS>.<SPI_CHIP_SELECT>`.
   - Configure SPI mode, bits per word, and speed.
   - Initialize the MCP23S17:
     - write `IOCON`
     - write `IODIRA=0x00`
     - write `GPIOA=0x00`
   - Maintain an in-memory `gpioaState`.
   - On relay activation, set bit `1 << DIDO_RELAY_PIN` and write `GPIOA`.
   - On relay deactivation, clear bit `1 << DIDO_RELAY_PIN` and write `GPIOA`.
   - Close the file descriptor on shutdown.

   Implementation options:

   - Use `golang.org/x/sys/unix` directly, consistent with `gatecontrol2`'s low-level
     serial implementation.
   - Or use a maintained SPI package if it works on ARMv6 without CGO and keeps
     deployment simple.

   If using `unix` directly, the implementation must issue Linux `SPI_IOC_*` ioctls.
   This is the main low-level risk area because Go does not expose a high-level spidev
   API in the standard library.

5. Rework `internal/app.Service` for DIDO.

   The Go service should no longer poll hardware every `500ms`.

   Suggested initial DIDO behavior:

   - On startup:
     - publish `availability=online` after DIDO initialization succeeds
     - publish initial `state=STOPPED`
   - On `open` command:
     - if assumed state is already `OPEN`, do nothing
     - otherwise publish `target_state=open`
     - pulse relay
     - publish `state=OPEN`
     - store assumed state `OPEN`
   - On `close` command:
     - if assumed state is already `CLOSED`, do nothing
     - otherwise publish `target_state=close`
     - pulse relay
     - publish `state=CLOSED`
     - store assumed state `CLOSED`
   - On pulse failure:
     - publish `availability=offline`
     - keep the previous assumed state
   - On clean shutdown:
     - turn relay off as best effort
     - publish `availability=offline`

   This intentionally matches the current Python DIDO limitations. It does not claim
   real gate position unless DIDO input feedback is added later.

6. Keep MQTT from `gatecontrol2`, with project naming updates.

   Suggested defaults:

   - `MQTT_BROKER=localhost`
   - `MQTT_PORT=1883`
   - `MQTT_CLIENT_ID=gatecontrol`
   - `MQTT_BASE_TOPIC=faac/gate`
   - `LOG_LEVEL=info`

   Keep retained MQTT messages for state, target state, and availability.

7. Replace configuration.

   Keep these from `gatecontrol2`:

   - `MQTT_BROKER`
   - `MQTT_PORT`
   - `MQTT_CLIENT_ID`
   - `MQTT_USERNAME`
   - `MQTT_PASSWORD`
   - `MQTT_BASE_TOPIC`
   - `LOG_LEVEL`
   - mock flags for local testing, if still useful

   Add or preserve these from `gatecontrol`:

   - `SPI_BUS`
   - `SPI_CHIP_SELECT`
   - `SPI_HARDWARE_ADDR`
   - `DIDO_RELAY_PIN`
   - `SPI_SPEED_HZ` with default `100000`
   - optionally `PULSE_LENGTH_MS` with default `500`

   Remove these:

   - `HOST`
   - `PORT`
   - `BASIC_AUTH_USERNAME`
   - `BASIC_AUTH_PASSWORD`
   - `WEBHOOK_URL`
   - `ACCESSORY_ID`
   - `USB_DEVICE`
   - `USB_BAUD`
   - `USE_MOCK_USB`

8. Rewrite tests around DIDO behavior.

   Test cases should cover:

   - Config defaults and environment parsing for MQTT and SPI.
   - Command normalization accepts only `open` and `close`.
   - `open` from `STOPPED` pulses once and publishes target/state.
   - `close` from `OPEN` pulses once and publishes target/state.
   - Duplicate `open` while assumed `OPEN` does not pulse.
   - Duplicate `close` while assumed `CLOSED` does not pulse.
   - Pulse failure publishes offline and does not update assumed state.
   - Shutdown calls hardware close and publishes offline.
   - SPI adapter builds the same MCP23S17 control bytes and register writes as Python.

   The hardware tests should not require a real Pi. Put register/control-byte logic in
   small functions that can be unit-tested without `/dev/spidev*`.

9. Update deployment artifacts.

   Update `documentation/gatecontrol.service`:

   - remove Python-specific `PYTHONPATH`
   - remove REST/webhook/basic-auth variables
   - add MQTT variables
   - keep SPI variables
   - change `ExecStart` to the Go binary path, for example:

   ```ini
   ExecStart=/home/pi/gatecontrol/gatecontrol
   ```

   Update README instructions:

   - install/build Go binary instead of Python requirements
   - document MQTT topics instead of REST endpoints
   - document ARMv6 build command:

   ```bash
   GOOS=linux GOARCH=arm GOARM=6 CGO_ENABLED=0 go build -o bin/gatecontrol-armv6 ./cmd/gatecontrol
   ```

10. Verify on target hardware.

    Local verification:

    - `go test ./...`
    - run with mock DIDO and mock MQTT if those flags are kept

    Raspberry Pi verification:

    - confirm `/dev/spidev0.0` exists
    - confirm SPI is enabled in `raspi-config` or `/boot/config.txt`
    - confirm service user can access the SPI device
    - run with `LOG_LEVEL=debug`
    - send MQTT command `open`
    - verify exactly one relay pulse on the DIDO board
    - send duplicate `open`
    - verify no second pulse while assumed state is `OPEN`
    - send `close`
    - verify exactly one relay pulse
    - reboot and verify systemd startup

## Open Questions

- Should the initial assumed state be `STOPPED`, as today, or should it be configurable
  as `OPEN`/`CLOSED` for restart behavior?
  Decision: Assume `CLOSED` as the initial assumed state.
- Should the service persist the last assumed state to disk so a restart does not forget
  whether the gate was last commanded open or closed?
  Decision: No, do not persist.
- Should MQTT payloads stay as `OPEN`/`CLOSED` for current state and `open`/`close` for
  target state, matching `gatecontrol2`, or should they use HomeKit numeric door states?
  Decision: Use exactly the same payloads as `gatecontrol2`.
- Which Homebridge/HomeKit MQTT plugin will consume the new topics? The old
  `homebridge-http-webhooks` integration will no longer apply directly.
  Decision: We will use `homebridge-mqttthing` with a simple MQTT door accessory configuration. This should however not be your concern as the goal is only to operate MQTT!
- Is only `Relay0` needed permanently, or should the Go DIDO package support all output
  pins for future expansion?
  Decision: If it is possible without much extra complexity, support all output pins. Otherwise, hardcode `Relay0` and add a TODO for future expansion.
- Does the DIDO board require active-high relay behavior in all deployments, or should
  relay polarity be configurable?
  Decision: I do not know this, try to research it. If you cannot find out limit your work to what is currently possible.
- Are FAAC `OUT 1` and `OUT 2` still physically connected to DIDO inputs anywhere? If so,
  the migration can later add real input feedback instead of assumed state.
  Decision: This is a future improvement. For now feedback pins are not connected.
- Which Raspberry Pi model is the production target now: original Zero/Zero W ARMv6 or
  Zero 2W ARM64? The build documentation should make one the default.
  Decision: It is the older model Zero W with ARMv6.

## Risks

- The Go SPI implementation is the riskiest new code. The current Python implementation
  relies on `spidev`; a Go replacement must correctly configure Linux spidev ioctls and
  byte transfers on Raspberry Pi.
- Without input feedback, MQTT state remains assumed state. It can become wrong if the
  gate is operated by a remote, keypad, wall switch, safety stop, obstacle detection, or
  power interruption.
- The USB service's polling/state code cannot be reused as-is. Keeping it would create a
  misleading architecture that expects unavailable FAAC position frames.
- MQTT changes the integration contract. Homebridge configuration must move away from
  HTTP webhooks or use an MQTT-capable bridge/plugin.
- GPIO expander initialization mistakes can leave relay outputs in the wrong state. The
  Go adapter should explicitly write relay off during startup and shutdown.
- SPI permissions differ by Raspberry Pi OS version. The systemd service may need group
  membership such as `spi` or a udev rule.
- Cross-compilation must remain compatible with ARMv6 if the original Pi Zero/Zero W is
  still used. Avoid CGO-only dependencies unless deployment builds happen directly on the
  Pi.

## Recommended First Implementation Slice

The safest first slice is:

1. Import Go config, MQTT, domain types, mocks, and tests from `gatecontrol2`.
2. Replace `GateTransport` with a minimal `GateHardware.Pulse` interface.
3. Implement service logic with mock DIDO only.
4. Get `go test ./...` passing locally.
5. Implement the Linux DIDO SPI adapter.
6. Test a single relay pulse on the Pi before connecting it to the FAAC input.
7. Update README and systemd service after the binary behavior is verified.
