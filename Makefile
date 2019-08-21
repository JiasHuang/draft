CFLAGS = -Werror -Wall
LDFLAGS =
LIBS =
OBJS = test.o
TARGET = test

include $(wildcard *.mk)

all: options $(TARGET)

options: options.h

options.h: options.py options.xml
	./options.py -i options.xml -o options.h

test: $(OBJS) options.h
	$(CROSS_COMPILE)gcc $(LDFLAGS) $(LIBS) -o $@ $^

%.o: %.c
	$(CROSS_COMPILE)gcc $(CFLAGS) $(INCS) -c $<

clean:
	rm -f *.o $(TARGET)
