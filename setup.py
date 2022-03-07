from setuptools import setup, Extension
import platform

is_windows = platform.system() == 'Windows'

backends = [Extension('compushady.backends.vulkan',
                      libraries=['vulkan-1' if is_windows else 'vulkan'],
                      sources=['compushady/backends/vulkan.cpp',
                               'compushady/backends/common.cpp']
                      )]


if is_windows:
    backends.append(Extension('compushady.backends.d3d12',
                              libraries=['dxgi', 'd3d12'],
                              sources=['compushady/backends/d3d12.cpp',
                                       'compushady/backends/dxgi.cpp',
                                       'compushady/backends/common.cpp', ]
                              ))
    backends.append(Extension('compushady.backends.d3d11',
                              libraries=['dxgi', 'd3d11'],
                              sources=['compushady/backends/d3d11.cpp',
                                       'compushady/backends/dxgi.cpp',
                                       'compushady/backends/common.cpp']
                              ))

backends.append(Extension('compushady.backends.dxc',
                          libraries=['d3dcompiler'] if is_windows else [],
                          sources=['compushady/backends/dxc.cpp',
                                   'compushady/backends/common.cpp']
                          ))

additional_files = []
if is_windows:
    additional_files = ['backends/dxcompiler.dll', 'backends/dxil.dll']
elif platform.system() == 'Linux':
    additional_files = ['backends/libdxcompiler.so.3.7']

setup(name='compushady',
      version='0.1',
      description='The compushady GPU Compute module',
      author='Roberto De Ioris',
      author_email='roberto.deioris@gmail.com',
      url='https://github.com/rdeioris/compushady',
      long_description='''
Run GPU Compute kernels from Python.
''',
      setup_requires=['wheel'],
      packages=['compushady', 'compushady.shaders'],
      package_data={'compushady': additional_files},
      ext_modules=backends,
      )
