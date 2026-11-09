import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
assert torch.cuda.is_available()
q=torch.randn(1,8,256,128,device='cuda',dtype=torch.bfloat16)
with sdpa_kernel(SDPBackend.FLASH_ATTENTION):
    result=torch.nn.functional.scaled_dot_product_attention(q,q,q,is_causal=True)
assert torch.isfinite(result).all().item()
print('FLASH_ATTENTION_HEALTH_CHECK_PASSED',torch.cuda.get_device_name(0))
