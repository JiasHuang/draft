#include <stdio.h>

#include "options.h"

static void print_usage(void *arg)
{
	printf("usage: %s [option]\n", (char*)arg);
}

int main(int argc, char *argv[])
{
	int i;
	static struct xopt opt;

	xopt_install_usage_callback(print_usage, argv[0]);
	xopt_parse_args(&opt, argc, argv);

	if (opt.show_version) {
	    printf("version: %d.%d\n", 1, 0);
	    return 0;
	}

	for (i=0; i<opt.input_cnt; i++)
	    printf("input[%d] %s\n", i, opt.input[i]);

	printf("output %s\n", opt.output);

	return 0;
}

