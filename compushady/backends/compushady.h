#include <Python.h>
#include "structmember.h"
#include <unordered_map>
#include <vector>

#define COMPUSHADY_CLEAR(x) memset(((char*)x) + sizeof(PyObject), 0, sizeof(*x) - sizeof(PyObject))

#define COMPUSHADY_ALIGN(x, alignment) ((x + alignment - 1) / alignment) * alignment

#define COMPUSHADY_HEAP_DEFAULT 0
#define COMPUSHADY_HEAP_UPLOAD 1
#define COMPUSHADY_HEAP_READBACK 2

#define COMPUSHADY_SHADER_BINARY_TYPE_DXIL 0
#define COMPUSHADY_SHADER_BINARY_TYPE_SPIRV 1
#define COMPUSHADY_SHADER_BINARY_TYPE_DXBC 2
#define COMPUSHADY_SHADER_BINARY_TYPE_MSL 3
#define COMPUSHADY_SHADER_BINARY_TYPE_GLSL 4

#define COMPUSHADY_SHADER_TARGET_TYPE_CS 0
#define COMPUSHADY_SHADER_TARGET_TYPE_LIB 1
#define COMPUSHADY_SHADER_TARGET_TYPE_VS 2
#define COMPUSHADY_SHADER_TARGET_TYPE_PS 3

#define COMPUSHADY_SAMPLER_FILTER_POINT 0
#define COMPUSHADY_SAMPLER_FILTER_LINEAR 1

#define COMPUSHADY_SAMPLER_ADDRESS_MODE_WRAP 0
#define COMPUSHADY_SAMPLER_ADDRESS_MODE_MIRROR 1
#define COMPUSHADY_SAMPLER_ADDRESS_MODE_CLAMP 2

#define R32G32B32A32_FLOAT 2
#define R32G32B32A32_UINT 3
#define R32G32B32A32_SINT 4
#define R32G32B32_FLOAT 6
#define R32G32B32_UINT 7
#define R32G32B32_SINT 8
#define R16G16B16A16_FLOAT 10
#define R16G16B16A16_UNORM 11
#define R16G16B16A16_UINT 12
#define R16G16B16A16_SNORM 13
#define R16G16B16A16_SINT 14
#define R32G32_FLOAT 16
#define R32G32_UINT 17
#define R32G32_SINT 18
#define R8G8B8A8_UNORM 28
#define R8G8B8A8_UNORM_SRGB 29
#define R8G8B8A8_UINT 30
#define R8G8B8A8_SNORM 31
#define R8G8B8A8_SINT 32
#define R16G16_FLOAT 34
#define R16G16_UNORM 35
#define R16G16_UINT 36
#define R16G16_SNORM 37
#define R16G16_SINT 38
#define R32_FLOAT 41
#define R32_UINT 42
#define R32_SINT 43
#define R8G8_UNORM 49
#define R8G8_UINT 50
#define R8G8_SNORM 51
#define R8G8_SINT 52
#define R16_FLOAT 54
#define R16_UNORM 55
#define R16_UINT 57
#define R16_SNORM 58
#define R16_SINT 59
#define R8_UNORM 61
#define R8_UINT 62
#define R8_SNORM 63
#define R8_SINT 64
#define B8G8R8A8_UNORM 87
#define B8G8R8A8_UNORM_SRGB 91

#define D32_FLOAT 40
#define D24_UNORM_S8_UINT 45
#define D16_UNORM 55

extern PyObject* Compushady_DeviceError;
extern PyObject* Compushady_BufferError;
extern PyObject* Compushady_Texture1DError;
extern PyObject* Compushady_Texture2DError;
extern PyObject* Compushady_Texture3DError;
extern PyObject* Compushady_SamplerError;
extern PyObject* Compushady_HeapError;

typedef struct compushady_backend_desc
{
	PyModuleDef py_module_def;

	PyTypeObject* device_type;
	PyMemberDef* device_members;
	PyMethodDef* device_methods;

	PyTypeObject* resource_type;
	PyMemberDef* resource_members;
	PyMethodDef* resource_methods;

	PyTypeObject* swapchain_type;
	PyMemberDef* swapchain_members;
	PyMethodDef* swapchain_methods;

	PyTypeObject* compute_type;
	PyMemberDef* compute_members;
	PyMethodDef* compute_methods;

	PyTypeObject* sampler_type;
	PyMemberDef* sampler_members;
	PyMethodDef* sampler_methods;

	PyTypeObject* heap_type;
	PyMemberDef* heap_members;
	PyMethodDef* heap_methods;
} compushady_backend_desc_t;

void compushady_backend_desc_init(
	compushady_backend_desc* compushady_backend, const char* name, PyMethodDef* backend_methods);

PyObject* compushady_backend_init(compushady_backend_desc_t* compushady_backend);

void compushady_backend_destroy(compushady_backend_desc* compushady_backend);

template <typename T>
bool compushady_check_descriptors(PyTypeObject* py_resource_type, PyObject* py_resources, std::vector<T*>& resources)
{
	if (py_resources)
	{
		PyObject* py_iter = PyObject_GetIter(py_resources);
		if (!py_iter)
		{
			return false;
		}
		while (PyObject* py_item = PyIter_Next(py_iter))
		{
			int ret = PyObject_IsInstance(py_item, (PyObject*)py_resource_type);
			if (ret < 0)
			{
				Py_DECREF(py_item);
				Py_DECREF(py_iter);
				return false;
			}
			else if (ret == 0)
			{
				Py_DECREF(py_item);
				Py_DECREF(py_iter);
				PyErr_Format(PyExc_ValueError, "Expected a Resource object");
				return false;
			}
			resources.push_back((T*)py_item);
			Py_DECREF(py_item);
		}
		Py_DECREF(py_iter);
	}

	return true;
}

#define COMPUSHADY_NEW_TYPE(name, type)                                                            \
	static PyTypeObject name##_##type##_Type = {                                                  \
		PyVarObject_HEAD_INIT(NULL, 0) "compushady.backends." #name "." #type, /* tp_name */         \
		sizeof(name##_##type), /* tp_basicsize */                                              \
		0, /* tp_itemsize */                                                                       \
		(destructor)name##_##type##_dealloc, /* tp_dealloc */                                    \
		0, /* tp_print */                                                                          \
		0, /* tp_getattr */                                                                        \
		0, /* tp_setattr */                                                                        \
		0, /* tp_reserved */                                                                       \
		0, /* tp_repr */                                                                           \
		0, /* tp_as_number */                                                                      \
		0, /* tp_as_sequence */                                                                    \
		0, /* tp_as_mapping */                                                                     \
		0, /* tp_hash  */                                                                          \
		0, /* tp_call */                                                                           \
		0, /* tp_str */                                                                            \
		0, /* tp_getattro */                                                                       \
		0, /* tp_setattro */                                                                       \
		0, /* tp_as_buffer */                                                                      \
		Py_TPFLAGS_DEFAULT, /* tp_flags */                                                         \
		"compushady " #name " " #type, /* tp_doc */                                                  \
	}

#define COMPUSHADY_NEW(type) (type*)PyObject_New(type, &type##_Type);