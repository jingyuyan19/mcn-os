import { defineField, defineType } from 'sanity'

export default defineType({
    name: 'prompt_config',
    title: '🧠 Brain Prompts',
    type: 'document',
    fields: [
        defineField({
            name: 'role',
            title: 'Role',
            type: 'string',
            options: {
                list: ['Analyst', 'Writer', 'Director'],
                layout: 'radio'
            }
        }),
        defineField({
            name: 'template',
            title: 'Prompt Template',
            type: 'text',
            rows: 15,
            description: 'Use {{variable}} placeholders'
        }),
        defineField({
            name: 'version',
            title: 'Version',
            type: 'string',
            initialValue: 'v1.0'
        }),
        defineField({
            name: 'description',
            title: 'Description',
            type: 'string'
        })
    ],
    preview: {
        select: {
            title: 'role',
            subtitle: 'version'
        }
    }
})
