#include <stdio.h>

#include "options.h"

int main(int argc, char *argv[])
{
	int i;
	static struct xopt opt;

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

