{
  description = "AYANEO AM-02 subscreen 데몬";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" ];
      forAll = nixpkgs.lib.genAttrs systems;
    in {
      packages = forAll (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in rec {
          default = am02-subscreen;
          am02-subscreen = pkgs.python3Packages.buildPythonApplication {
            pname = "am02-subscreen";
            version = "0.1.0";
            src = ./.;
            format = "other";
            propagatedBuildInputs = [ pkgs.python3Packages.pyserial ];
            installPhase = ''
              # 패키지 디렉터리는 Python 임포트명(am02_subscreen, 밑줄)과 일치해야 함
              mkdir -p $out/bin $out/lib/am02_subscreen $out/share/am02-subscreen
              cp -r src/am02_subscreen/. $out/lib/am02_subscreen/
              # main.py 기본 레이아웃 경로(__file__ parents[2])는 Nix store 내에서
              # 해석되지 않으므로 data file로 별치 설치 후 ExecStart에서 --layout으로 명시 전달
              cp layout.json $out/share/am02-subscreen/layout.json
              cat > $out/bin/am02-subscreend <<EOF
#!${pkgs.python3}/bin/python3
import sys; sys.path.insert(0, "$out/lib")
from am02_subscreen.main import main
main()
EOF
              chmod +x $out/bin/am02-subscreend
            '';
            meta = {
              description = "AYANEO AM-02 subscreen daemon - CPU/GPU temps over /dev/ttyS0";
              mainProgram = "am02-subscreend";
              license = pkgs.lib.licenses.mit;
              platforms = [ "x86_64-linux" ];
            };
          };
        });
      overlays.default = final: prev: {
        am02-subscreen = self.packages.${final.system}.am02-subscreen;
      };
      nixosModules.default = { pkgs, ... }: {
        # 모듈이 pkgs.am02-subscreen을 참조하므로 overlay를 함께 구성
        nixpkgs.overlays = [ self.overlays.default ];
        imports = [ ./nix/module.nix ];
      };
    };
}
