IMAGE ?= reverse-engineering-lab:local
CC := gcc

# Arc 1 (parts 1 to 5): no optimization, no PIE, debug info, so the
# disassembly stays close to the source and addresses stay fixed.
ARC1_CFLAGS := -O0 -g -fno-pie -no-pie

BINARIES := part-01/hello

.PHONY: build image shell test versions clean

build: $(BINARIES)

part-01/%: part-01/%.c
	$(CC) $(ARC1_CFLAGS) -o $@ $<

image:
	docker build -t $(IMAGE) .

shell: image
	docker run --rm -it $(IMAGE)

test:
	python3 -m unittest discover -s tests -v

versions: image
	docker run --rm $(IMAGE) sh -c \
	  'gcc --version | head -1; objdump --version | head -1; gdb --version | head -1'

clean:
	rm -f $(BINARIES)
