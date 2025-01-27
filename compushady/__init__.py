import importlib
from . import config
import atexit
import os

HEAP_DEFAULT = 0
HEAP_UPLOAD = 1
HEAP_READBACK = 2

SHADER_BINARY_TYPE_DXIL = 0
SHADER_BINARY_TYPE_SPIRV = 1
SHADER_BINARY_TYPE_DXBC = 2
SHADER_BINARY_TYPE_MSL = 3
SHADER_BINARY_TYPE_GLSL = 4

SHADER_TARGET_TYPE_CS = 0
SHADER_TARGET_TYPE_LIB = 1
SHADER_TARGET_TYPE_VS = 2
SHADER_TARGET_TYPE_PS = 3

SAMPLER_FILTER_POINT = 0
SAMPLER_FILTER_LINEAR = 1

SAMPLER_ADDRESS_MODE_WRAP = 0
SAMPLER_ADDRESS_MODE_MIRROR = 1
SAMPLER_ADDRESS_MODE_CLAMP = 2


class UnknownBackend(Exception):
    pass


class DeviceException(Exception):
    pass


class BufferException(Exception):
    pass


class Texture1DException(Exception):
    pass


class Texture2DException(Exception):
    pass


class Texture3DException(Exception):
    pass


class SamplerException(Exception):
    pass


class HeapException(Exception):
    pass


_backend = None
_discovered_devices = None
_current_device = None


def get_backend():
    def debug_callback():
        messages = get_current_device().get_debug_messages()
        for message in messages:
            print(message)

    global _backend
    if _backend is None:
        _backend = importlib.import_module(
            "compushady.backends.{0}".format(config.wanted_backend)
        )
        if config.debug:
            _backend.enable_debug()
            atexit.register(debug_callback)
    return _backend


def get_discovered_devices():
    global _discovered_devices
    if _discovered_devices is None:
        _discovered_devices = get_backend().get_discovered_devices()
    return _discovered_devices


def set_current_device(index):
    global _current_device
    _current_device = get_discovered_devices()[index]


def get_current_device():
    global _current_device
    if _current_device is None:
        _current_device = get_best_device()
    return _current_device


def get_best_device():
    if "COMPUSHADY_DEVICE" in os.environ:
        return get_discovered_devices()[int(os.environ["COMPUSHADY_DEVICE"])]
    return sorted(
        get_discovered_devices(),
        key=lambda x: (x.is_hardware, x.is_discrete, x.dedicated_video_memory),
    )[-1]


class Resource:
    def copy_to(self, destination):
        self.handle.copy_to(destination.handle)

    @property
    def size(self):
        return self.handle.size


class Buffer(Resource):
    def __init__(
        self,
        size,
        heap_type=HEAP_DEFAULT,
        stride=0,
        format=0,
        heap=None,
        heap_offset=0,
        device=None,
    ):
        self.device = device if device else get_current_device()
        self.heap = heap
        self.handle = self.device.create_buffer(
            heap_type, size, stride, format, heap.handle if heap else None, heap_offset
        )

    def upload(self, data, offset=0):
        self.handle.upload(data, offset)

    def upload2d(self, data, pitch, width, height, bytes_per_pixel):
        return self.handle.upload2d(data, pitch, width, height, bytes_per_pixel)

    def upload_chunked(self, data, stride, filler):
        return self.handle.upload_chunked(data, stride, filler)

    def readback(self, buffer_or_size=0, offset=0):
        if isinstance(buffer_or_size, int):
            return self.handle.readback(buffer_or_size, offset)
        self.handle.readback_to_buffer(buffer_or_size, offset)

    def readback2d(self, pitch, width, height, bytes_per_pixel):
        return self.handle.readback2d(pitch, width, height, bytes_per_pixel)


class Texture1D(Resource):
    def __init__(self, width, format, heap=None, heap_offset=0, device=None):
        self.device = device if device else get_current_device()
        self.heap = heap
        self.handle = self.device.create_texture1d(
            width, format, heap.handle if heap else None, heap_offset
        )

    @classmethod
    def from_native(cls, ptr, device=None):
        instance = cls.__new__(cls)
        instance.device = device if device else get_current_device()
        instance.handle = instance.device.create_texture1d_from_native(ptr)
        return instance

    @property
    def width(self):
        return self.handle.width

    @property
    def row_pitch(self):
        return self.handle.row_pitch


class Texture2D(Resource):
    def __init__(self, width, height, format, heap=None, heap_offset=0, device=None):
        self.device = device if device else get_current_device()
        self.heap = heap
        self.handle = self.device.create_texture2d(
            width, height, format, heap.handle if heap else None, heap_offset
        )

    @classmethod
    def from_native(cls, ptr, width, height, format, device=None):
        instance = cls.__new__(cls)
        instance.device = device if device else get_current_device()
        instance.handle = instance.device.create_texture2d_from_native(
            ptr, width, height, format
        )
        return instance

    @property
    def width(self):
        return self.handle.width

    @property
    def height(self):
        return self.handle.height

    @property
    def row_pitch(self):
        return self.handle.row_pitch


class Texture3D(Resource):
    def __init__(
        self, width, height, depth, format, heap=None, heap_offset=0, device=None
    ):
        self.device = device if device else get_current_device()
        self.heap = heap
        self.handle = self.device.create_texture3d(
            width, height, depth, format, heap.handle if heap else None, heap_offset
        )

    @classmethod
    def from_native(cls, ptr, device=None):
        instance = cls.__new__(cls)
        instance.device = device if device else get_current_device()
        instance.handle = instance.device.create_texture3d_from_native(ptr)
        return instance

    @property
    def width(self):
        return self.handle.width

    @property
    def height(self):
        return self.handle.height

    @property
    def depth(self):
        return self.handle.depth

    @property
    def row_pitch(self):
        return self.handle.row_pitch


class BLAS(Resource):
    def __init__(self, vertex_buffer, index_buffer=None, device=None):
        self.device = device if device else get_current_device()
        self.handle = self.device.create_blas(
            vertex_buffer.handle, index_buffer.handle if index_buffer else None
        )


class TLAS(Resource):
    def __init__(self, blas, device=None):
        self.device = device if device else get_current_device()
        self.handle = self.device.create_tlas(blas.handle)


class Swapchain:
    def __init__(
        self, window_handle, format, num_buffers=3, device=None, width=0, height=0
    ):
        self.device = device if device else get_current_device()
        self.handle = self.device.create_swapchain(
            window_handle, format, num_buffers, width, height
        )

    @property
    def width(self):
        return self.handle.width

    @property
    def height(self):
        return self.handle.height

    def present(self, resource, x=0, y=0):
        self.handle.present(resource.handle, x, y)


class Sampler:
    def __init__(
        self,
        address_mode_u=SAMPLER_ADDRESS_MODE_WRAP,
        address_mode_v=SAMPLER_ADDRESS_MODE_WRAP,
        address_mode_w=SAMPLER_ADDRESS_MODE_WRAP,
        filter_min=SAMPLER_FILTER_POINT,
        filter_mag=SAMPLER_FILTER_POINT,
        device=None,
    ):
        self.device = device if device else get_current_device()
        self.handle = self.device.create_sampler(
            address_mode_u, address_mode_v, address_mode_w, filter_min, filter_mag
        )


class Heap:
    def __init__(self, heap_type, size, device=None):
        self.device = device if device else get_current_device()
        self.handle = self.device.create_heap(heap_type, size)

    @property
    def size(self):
        return self.handle.size

    @property
    def heap_type(self):
        return self.handle.heap_type


class Compute:
    def __init__(self, shader, cbv=[], srv=[], uav=[], samplers=[], device=None):
        self.device = device if device else get_current_device()
        self.handle = self.device.create_compute(
            shader,
            cbv=[resource.handle for resource in cbv],
            srv=[resource.handle for resource in srv],
            uav=[resource.handle for resource in uav],
            samplers=[sampler.handle for sampler in samplers],
        )

    def dispatch(self, x, y, z):
        self.handle.dispatch(x, y, z)


class RayTracer:
    def __init__(self, shader, cbv=[], srv=[], uav=[], samplers=[], device=None):
        self.device = device if device else get_current_device()
        self.handle = self.device.create_raytracer(
            shader,
            cbv=[resource.handle for resource in cbv],
            srv=[resource.handle for resource in srv],
            uav=[resource.handle for resource in uav],
            samplers=[sampler.handle for sampler in samplers],
        )

    def dispatch_rays(self, x, y, z):
        self.handle.dispatch_rays(x, y, z)


class Rasterizer:
    def __init__(
        self,
        vertex_shader,
        pixel_shader,
        rtv=[],
        dsv=None,
        cbv=[],
        srv=[],
        uav=[],
        samplers=[],
        wireframe=False,
        device=None,
    ):
        self.device = device if device else get_current_device()
        self.handle = self.device.create_rasterizer(
            vertex_shader,
            pixel_shader,
            rtv=[resource.handle for resource in rtv],
            dsv=dsv.handle if dsv else None,
            cbv=[resource.handle for resource in cbv],
            srv=[resource.handle for resource in srv],
            uav=[resource.handle for resource in uav],
            samplers=[sampler.handle for sampler in samplers],
            wireframe=wireframe,
        )

    def draw(self, number_of_vertices, number_of_instances=1):
        self.handle.draw(number_of_vertices, number_of_instances)
