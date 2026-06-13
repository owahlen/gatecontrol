package domain

import "testing"

func TestNormalizeCommand(t *testing.T) {
	t.Parallel()

	tests := []struct {
		input string
		want  Command
		ok    bool
	}{
		{input: "open", want: CommandOpen, ok: true},
		{input: " OPEN ", want: CommandOpen, ok: true},
		{input: "close", want: CommandClose, ok: true},
		{input: "CLOSE", want: CommandClose, ok: true},
		{input: "stop", ok: false},
		{input: "", ok: false},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.input, func(t *testing.T) {
			t.Parallel()
			got, ok := NormalizeCommand(tc.input)
			if ok != tc.ok {
				t.Fatalf("ok mismatch: got=%v want=%v", ok, tc.ok)
			}
			if got != tc.want {
				t.Fatalf("command mismatch: got=%q want=%q", got, tc.want)
			}
		})
	}
}
