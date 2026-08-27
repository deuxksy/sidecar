# ayaneo-am02-subscreen

A Linux daemon that feeds the AYANEO AM-02's front subscreen (clock, CPU/GPU
temperatures) over the internal serial link — a replacement for the
Windows-only AYASPACE feeder. Runs as a systemd service on NixOS (or any
Linux with Python 3 + pyserial).

## Status

Protocol **confirmed (v2)** via 3-way cross-validation (AYASPACE reverse
engineering, on-hardware probing, community MCU-side decompilation) — see
[docs/okf/reference/protocol.md](docs/okf/reference/protocol.md). On-hardware acceptance passed the 60 s
frame-rate check and screen readout (clock/temps) on 2026-08-25; cold-boot
autostart verification is in progress. The subscreen sits on a native UART at
`/dev/ttyS0` (115200 8N1).

## Architecture

```text
sensors.py          protocol.py                  transport.py
hwmon sysfs ──collect()──▶ layout.json ──encode()──▶ /dev/ttyS0 (115200 8N1)
(temp by name/label)      frame template                ^ reopen + backoff
                          + field offsets               on write failure
                                 ▲
                          layout.json — injection point once the
                          real protocol is captured
```

## Docs

- [Protocol spec (v2)](docs/okf/reference/protocol.md) — wire format, payload mapping, MCU RTC latch
- [Phase 0 diagnostics](docs/okf/explanation/phase0.md) — hardware discovery, probe experiments, reverse-engineering notes

## NixOS usage

Add the flake input and enable the service:

```nix
{
  inputs.am02-subscreen.url = "github:deuxksy/ayaneo-am02-subscreen";

  # in your NixOS configuration:
  imports = [ am02-subscreen.nixosModules.default ];

  services.am02-subscreen.enable = true;
  # services.am02-subscreen.port = "/dev/ttyS0";  # default
}
```

## Development

```bash
# run the test suite (no hardware needed — tests use pyserial loop://)
uv run pytest

# build the package
nix build .#am02-subscreen
```

## Roadmap

- [x] Capture the display protocol (AYASPACE binary static analysis, MITM-free)
- [x] Replace the placeholder `layout.json` with the real frame layout
- [ ] On-hardware acceptance — frame rate ✅, clock ✅, temp ✅; cold-boot autostart & suspend/resume in progress

Hardware structure (native UART, not USB) was established thanks to the
[r/ayaneo AM-02 subscreen customization thread](https://www.reddit.com/r/ayaneo/comments/1isly3s/the_ayaneo_am02_subscreen_customization/).

## License

[MIT](LICENSE)
