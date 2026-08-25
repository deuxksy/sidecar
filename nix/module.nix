{ config, lib, pkgs, ... }:
let
  cfg = config.services.am02-subscreen;
in {
  options.services.am02-subscreen = {
    enable = lib.mkEnableOption "AM02 subscreen 시스템 정보 데몬";
    port = lib.mkOption {
      type = lib.types.str;
      default = "/dev/ttyS0";
      description = "subscreen 연결 시리얼 포트";
    };
  };
  config = lib.mkIf cfg.enable {
    users.users.am02-sub = {
      isSystemUser = true;
      group = "dialout";  # /dev/ttyS0 root:dialout 660
      home = "/var/empty";
    };
    systemd.services.am02-subscreen = {
      description = "AM02 subscreen system info daemon";
      after = [ "dev-ttyS0.device" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        # --layout 명시 필수: main.py 기본 경로는 Nix store에서 해석 불가
        ExecStart = "${pkgs.am02-subscreen}/bin/am02-subscreend ${cfg.port} --layout ${pkgs.am02-subscreen}/share/am02-subscreen/layout.json";
        User = "am02-sub";
        Restart = "always";
        RestartSec = "5";
      };
    };
  };
}
