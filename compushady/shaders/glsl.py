from compushady.backends import dxc
from compushady import get_backend, SHADER_TARGET_TYPE_CS, SHADER_TARGET_TYPE_VS, SHADER_TARGET_TYPE_PS, SHADER_BINARY_TYPE_SPIRV

SHADER_BINARY_TYPE_GLSL, SHADER_TARGET_TYPE_GLSL
import os
import platform
import pyshaderc


shaderc_stages_mapping = {
    SHADER_TARGET_TYPE_VS: "vert",
    SHADER_TARGET_TYPE_PS: "frag",
    SHADER_TARGET_TYPE_CS : "comp"
}

def compile(source, entry_point="main", target_type=SHADER_TARGET_TYPE_CS):
    wantedBinaryType = get_backend().get_shader_binary_type()
    if(wantedBinaryType == SHADER_BINARY_TYPE_SPIRV):
        sourceBytes = source.encode(encoding='UTF-8')
        stage = shaderc_stages_mapping[target_type]
        blob = pyshaderc.compile_into_spirv(sourceBytes, stage)
        return blob
    raise ValueError("Backend not supported with glsl shaders.")
