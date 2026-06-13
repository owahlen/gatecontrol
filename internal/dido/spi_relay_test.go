package dido

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestControlByteMatchesPythonImplementation(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name         string
		hardwareAddr int
		write        bool
		want         byte
	}{
		{name: "write addr 0", hardwareAddr: 0, write: true, want: 0x40},
		{name: "read addr 0", hardwareAddr: 0, write: false, want: 0x41},
		{name: "write addr 1", hardwareAddr: 1, write: true, want: 0x42},
		{name: "write addr 7", hardwareAddr: 7, write: true, want: 0x4E},
		{name: "read addr 7", hardwareAddr: 7, write: false, want: 0x4F},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := controlByte(tc.hardwareAddr, tc.write); got != tc.want {
				t.Fatalf("controlByte=%#02x want=%#02x", got, tc.want)
			}
		})
	}
}

func TestWriteFrame(t *testing.T) {
	t.Parallel()

	got := writeFrame(2, registerGPIOA, 0x08)
	want := []byte{0x44, 0x12, 0x08}
	assertFrames(t, got, want)
}

func TestNewRelayInitializesMCP23S17(t *testing.T) {
	t.Parallel()

	conn := &fakeSPIConn{}
	relay, err := newRelay(conn, 0, 0, time.Millisecond)
	if err != nil {
		t.Fatalf("newRelay: %v", err)
	}
	defer relay.Close()

	want := [][]byte{
		{0x40, registerIOCON, 0x28},
		{0x40, registerIODIRA, 0x00},
		{0x40, registerGPIOA, 0x00},
	}
	assertFrameList(t, conn.frames, want)
}

func TestPulseSetsAndClearsConfiguredRelayPin(t *testing.T) {
	t.Parallel()

	conn := &fakeSPIConn{}
	relay, err := newRelay(conn, 0, 3, time.Millisecond)
	if err != nil {
		t.Fatalf("newRelay: %v", err)
	}
	defer relay.Close()

	if err := relay.Pulse(context.Background()); err != nil {
		t.Fatalf("pulse: %v", err)
	}

	want := [][]byte{
		{0x40, registerIOCON, 0x28},
		{0x40, registerIODIRA, 0x00},
		{0x40, registerGPIOA, 0x00},
		{0x40, registerGPIOA, 0x08},
		{0x40, registerGPIOA, 0x00},
	}
	assertFrameList(t, conn.frames[:5], want)
}

func TestPulseClearsRelayWhenContextIsCanceled(t *testing.T) {
	t.Parallel()

	conn := &fakeSPIConn{}
	relay, err := newRelay(conn, 0, 1, time.Hour)
	if err != nil {
		t.Fatalf("newRelay: %v", err)
	}
	defer relay.Close()

	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := relay.Pulse(ctx); !errors.Is(err, context.Canceled) {
		t.Fatalf("pulse error=%v want context.Canceled", err)
	}

	want := [][]byte{
		{0x40, registerIOCON, 0x28},
		{0x40, registerIODIRA, 0x00},
		{0x40, registerGPIOA, 0x00},
		{0x40, registerGPIOA, 0x02},
		{0x40, registerGPIOA, 0x00},
	}
	assertFrameList(t, conn.frames[:5], want)
}

func TestCloseTurnsRelayOff(t *testing.T) {
	t.Parallel()

	conn := &fakeSPIConn{}
	relay, err := newRelay(conn, 0, 2, time.Millisecond)
	if err != nil {
		t.Fatalf("newRelay: %v", err)
	}
	if err := relay.SetRelay(true); err != nil {
		t.Fatalf("set relay: %v", err)
	}
	if err := relay.Close(); err != nil {
		t.Fatalf("close: %v", err)
	}

	if !conn.closed {
		t.Fatalf("expected conn closed")
	}
	last := conn.frames[len(conn.frames)-1]
	assertFrames(t, last, []byte{0x40, registerGPIOA, 0x00})
}

type fakeSPIConn struct {
	frames [][]byte
	closed bool
}

func (f *fakeSPIConn) Tx(w, _ []byte) error {
	frame := make([]byte, len(w))
	copy(frame, w)
	f.frames = append(f.frames, frame)
	return nil
}

func (f *fakeSPIConn) Close() error {
	f.closed = true
	return nil
}

func assertFrameList(t *testing.T, got [][]byte, want [][]byte) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("frame count=%d want=%d got=% X want=% X", len(got), len(want), got, want)
	}
	for i := range want {
		assertFrames(t, got[i], want[i])
	}
}

func assertFrames(t *testing.T, got []byte, want []byte) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("frame length=%d want=%d got=% X want=% X", len(got), len(want), got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("frame=% X want=% X", got, want)
		}
	}
}
