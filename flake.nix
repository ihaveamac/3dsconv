{
  inputs = {
    # Nix Utils
    nixpkgs.url = "nixpkgs/nixos-22.11";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems =
        [ "x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin" ];
      perSystem = { self', inputs', pkgs, ... }:
        let
          py3dsconv = pkgs.python3Packages.buildPythonPackage {
            name = "3dsconv";
            src = ./.;

            doCheck = false;
            propagatedBuildInputs = [ pkgs.python3Packages.pyaes ];
          };
        in {
          packages.py3dsconv = py3dsconv;
          packages.default = self'.packages.py3dsconv;

          devShells.default = pkgs.mkShellNoCC { inputsFrom = [ py3dsconv ]; };
        };
    };
}
