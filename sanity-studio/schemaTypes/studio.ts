// Schema: Studio (摄影棚)
// Background/scene assets with ComfyUI payload
// ⚠️ Critical Fix: Includes comfy_payload for GPU pipeline connectivity

export default {
    name: 'studio',
    title: '🎬 摄影棚',
    type: 'document',
    fields: [
        {
            name: 'name',
            title: '场景名称',
            type: 'string',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'category',
            title: '类型',
            type: 'string',
            options: {
                list: [
                    { title: '办公室', value: 'office' },
                    { title: '户外', value: 'outdoor' },
                    { title: '演播室', value: 'broadcast' },
                    { title: '虚拟', value: 'virtual' }
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
            description: '供管理员识别用的场景预览图'
        },
        // 🔧 Critical Fix: GPU Pipeline Connectivity
        {
            name: 'comfy_payload',
            title: '⚙️ ComfyUI 参数包 (JSON)',
            type: 'text',
            rows: 5,
            description: `给机器看的参数。例:
{
  "background_prompt": "modern office with glass windows, professional lighting",
  "negative_prompt": "cartoon, anime, low quality",
  "lora_name": "office_bg_v2.safetensors",
  "strength": 0.6
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
        },
        // Optional: Cached background video for Wan 2.2  
        {
            name: 'cached_video',
            title: '缓存背景视频 (本地路径)',
            type: 'string',
            description: '可选。已渲染好的背景视频本地路径，跳过重复生成'
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
