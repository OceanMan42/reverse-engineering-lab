# Reverse Engineering lab

The lab for the Reverse Engineering series on the 0x4142 blog. Every
binary and every terminal session shown in the series comes from this
image, so what you see in the posts is what you get here.

## Run it

    docker run --rm -it ghcr.io/oceanman42/reverse-engineering-lab

or build it yourself:

    git clone https://github.com/OceanMan42/reverse-engineering-lab
    cd reverse-engineering-lab
    make shell

Each part of the series has a folder: `part-01/` holds the source and the
compiled binary for part 1, and so on.

## For the author

- `make capture BLOG=../0x4142` rebuilds the image, runs every scenario in
  `captures/`, and writes capture JSON into the blog. Run `git diff` in the
  blog afterwards to see what changed (useful after a toolchain update).
- `make test` runs the capture script's tests.
- `make versions` prints the toolchain versions baked into the image.
