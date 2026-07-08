{
  description = "MIRA – dev shell with pixi, FFmpeg 7, and Python 3.12";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            # Environment manager – pixi handles Python packages via uv/pip
            pixi

            # Python (used as the host interpreter by pixi's conda env)
            python312

            # FFmpeg 7 – torchcodec links against its shared libs at runtime
            ffmpeg_7

            # Build toolchain needed by compiled Python packages (lpips, torch extensions, etc.)
            gcc
            gnumake
            cmake
            pkg-config

            # System libs that pip wheels / torch may dlopen
            zlib
            openssl
          ];

          shellHook = ''
            echo "MIRA dev shell (Nix) – run 'pixi run setup' or 'pixi run setup-cpu' to install Python deps"
          '';
        };
      }
    );
}
