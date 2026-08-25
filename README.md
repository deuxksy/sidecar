# ayaneo-am02-subscreen

A Linux daemon that feeds the AYANEO AM-02's front subscreen (clock, CPU/GPU
temperatures) over the internal serial link — a replacement for the
Windows-only AYASPACE feeder. Runs as a systemd service on NixOS (or any
Linux with Python 3 + pyserial).

## Status

**WORK IN PROGRESS.** The subscreen display protocol is still being
reverse-engineered, so `layout.json` is a placeholder and the screen will not
update yet. The hardware layer is verified: the subscreen sits on a native
UART at `/dev/ttyS0` (115200 8N1).

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
uv run --no-project --with pytest --with pyserial python -m pytest tests/

# build the package
nix build .#am02-subscreen
```

## Roadmap

- [ ] Capture the display protocol from Windows (AYASPACE serial traffic)
- [ ] Replace the placeholder `layout.json` with the real frame layout
- [ ] On-hardware acceptance: clock refresh, temp accuracy, suspend/resume

Hardware structure (native UART, not USB) was established thanks to the
[r/ayaneo AM-02 subscreen customization thread](https://www.reddit.com/r/ayaneo/comments/1isly3s/the_ayaneo_am02_subscreen_customization/).

## License

[MIT](LICENSE)
