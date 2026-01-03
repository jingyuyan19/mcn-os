// Schema: Wardrobe (衣橱)
// Clothing assets with ComfyUI LoRA payload
// ⚠️ Critical Fix: Includes comfy_payload for GPU pipeline connectivity

export default {
    name: 'wardrobe',
    title: '👔 衣橱',
    type: 'document',
    fields: [
        {
            name: 'name',
            title: '服装名称',
            type: 'string',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'category',
            title: '类型',
            type: 'string',
            options: {
                list: [
                    { title: '正装', value: 'formal' },
                    { title: '休闲', value: 'casual' },
                    { title: '运动', value: 'sport' },
                    { title: '特殊', value: 'special' }
                ]
            }
        },
        {
            name: 'preview',
            title: '预览图',
            type: 'image',
            options: {
                hotspot: true
            },
            description: '供管理员识别用的预览图'
        },
        // 🔧 Critical Fix: GPU Pipeline Connectivity
        {
            name: 'comfy_payload',
            title: '⚙️ ComfyUI 参数包 (JSON)',
            type: 'text',
            rows: 5,
            description: `给机器看的参数。例:
{
  "lora_name": "suit_v1.safetensors",
  "trigger_word": "navy blue suit, formal attire",
  "strength": 0.8
}`,
            validation: (Rule: any) => Rule.required().custom((value: string) => {
                if (!value) return 'ComfyUI 参数包是必填项'
                try {
                    JSON.parse(value)
                    return true
                } catch {
                    return 'JSON 格式无效'
                }
            })
        }
    ],
    preview: {
        select: {
            title: 'name',
            subtitle: 'category',
            media: 'preview'
        }
    }
}
