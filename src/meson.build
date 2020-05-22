opt_cmd = find_program('options.py')

gen = generator(
	opt_cmd,
	output : '@BASENAME@.h',
	arguments : ['-i', '@INPUT@', '-o', '@OUTPUT@'])

gen_h = gen.process(meson.current_source_dir()+'/options.xml')

executable('demo', 'demo.c', gen_h)
