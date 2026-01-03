import { defineConfig } from 'sanity'
import { structureTool } from 'sanity/structure'
import { visionTool } from '@sanity/vision'
import { schemaTypes } from './schemaTypes'
import DocumentsPane from 'sanity-plugin-documents-pane'

// Custom desk structure for organized navigation
const deskStructure = (S: any) =>
    S.list()
        .title('MCN 中控台')
        .items([
            // 艺人管理
            S.listItem()
                .id('artist-group')
                .title('🎭 艺人管理')
                .child(
                    S.list()
                        .title('艺人管理')
                        .id('artist-mgmt')
                        .items([
                            S.listItem()
                                .id('artist-list-item')
                                .title('艺人档案')
                                .child(S.documentTypeList('artist').title('艺人档案')),
                            S.listItem()
                                .id('voice-list-item')
                                .title('音色库')
                                .child(S.documentTypeList('voice').title('音色库')),
                        ])
                ),
            // 资产库
            S.listItem()
                .id('assets-group')
                .title('📦 资产库')
                .child(
                    S.list()
                        .title('资产库')
                        .id('assets')
                        .items([
                            S.listItem()
                                .id('wardrobe-list-item')
                                .title('衣橱')
                                .child(S.documentTypeList('wardrobe').title('衣橱')),
                            S.listItem()
                                .id('studio-list-item')
                                .title('摄影棚')
                                .child(S.documentTypeList('studio').title('摄影棚')),
                            S.listItem()
                                .id('source-list-item')
                                .title('情报源')
                                .child(S.documentTypeList('source').title('情报源')),
                        ])
                ),
            // 生产调度
            S.listItem()
                .id('production-group')
                .title('📅 生产调度')
                .child(
                    S.list()
                        .title('生产调度')
                        .id('production')
                        .items([
                            S.listItem()
                                .id('schedule-list-item')
                                .title('档期安排')
                                .child(S.documentTypeList('schedule').title('档期安排')),
                            S.listItem()
                                .id('post-list-item')
                                .title('视频工单')
                                .child(S.documentTypeList('post').title('视频工单')),
                        ])
                ),
            S.divider(),
            // Quick access to all documents
            ...S.documentTypeListItems().filter(
                (listItem: any) => !['artist', 'voice', 'wardrobe', 'studio', 'source', 'schedule', 'post'].includes(listItem.getId())
            ),
        ])

export default defineConfig({
    name: 'default',
    title: 'MCN 中控台',

    // User's Sanity project
    projectId: '4t6f8tmh',  // From sanity.io/manage
    dataset: 'production',

    plugins: [
        structureTool({
            structure: deskStructure,
            defaultDocumentNode: (S, { schemaType }) => {
                // Only apply to 'artist' documents
                if (schemaType === 'artist') {
                    return S.document().views([
                        S.view.form(), // Default form view

                        // View 2: Related Schedules
                        S.view
                            .component(DocumentsPane)
                            .options({
                                query: `*[_type == "schedule" && references($id)]`,
                                params: ({ document }: any) => ({
                                    id: document?.displayed?._id?.replace(/^drafts\./, '')
                                }),
                                initialValueTemplates: ({ document }: any) => [
                                    {
                                        id: 'schedule-for-artist',
                                        template: 'schedule-for-artist',
                                        title: 'Create New Schedule',
                                        schemaType: 'schedule',
                                        parameters: { artistId: document?.displayed?._id?.replace(/^drafts\./, '') }
                                    }
                                ],
                                useUndefinedId: true, // Handle new documents
                                options: { perspective: 'previewDrafts' }
                            })
                            .id('upcoming-schedules') // Added safe ID
                            .title('📅 Upcoming Schedules'),

                        // View 3: Related Posts (Work Orders)
                        S.view
                            .component(DocumentsPane)
                            .options({
                                query: `*[_type == "post" && references($id)]`,
                                params: ({ document }: any) => ({
                                    id: document?.displayed?._id?.replace(/^drafts\./, '')
                                }),
                                useUndefinedId: true,
                                options: { perspective: 'previewDrafts' }
                            })
                            .id('work-orders') // Added safe ID
                            .title('🎬 Work Orders'),
                    ])
                }
                return S.document().views([S.view.form()])
            },
        }),
        visionTool(),
    ],

    schema: {
        types: schemaTypes,
        templates: (prev) => [
            ...prev,
            {
                id: 'schedule-for-artist',
                title: 'Schedule for Artist',
                schemaType: 'schedule',
                value: (params: any) => ({
                    artist: { _type: 'reference', _ref: params.artistId },
                }),
            },
        ],
    },
})
