obj-m := acer-nitro-ec.o

KDIR  ?= /lib/modules/$(shell uname -r)/build
PWD   := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

# Default to GCC; pass LLVM=1 if kernel was built with Clang/LLVM
LLVM ?=

all:
	$(MAKE) -C $(KDIR) M=$(PWD) LLVM=$(LLVM) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

install:
	$(MAKE) -C $(KDIR) M=$(PWD) LLVM=$(LLVM) modules_install
	depmod -a

.PHONY: all clean install
