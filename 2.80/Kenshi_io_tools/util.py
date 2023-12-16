
import time
from datetime import datetime
from functools import wraps
from typing import Dict, Tuple


def func_timer(func):
    @wraps(func)
    def new_function(*args, **kwargs):
        start_at = time.time()
        # start_str = datetime.fromtimestamp(start_at).strftime('%Y-%m-%d %H:%I:%S')

        result = func(*args, **kwargs)

        end_at = time.time()
        # end_str = datetime.fromtimestamp(end_at).strftime('%Y-%m-%d %H:%I:%S')
        time_taken = end_at - start_at

        print('func:', func.__name__, 'took', '{:.3f}'.format(time_taken))

        return result
    return new_function


def code_page_list() :
    cp_list = [
        ('utf-8', 'utf-8', ''),
        ('euc_kr', 'euc_kr', ''),
        ('gb2312', 'gb2312', ''),
        ('koi8_r', 'koi8_r', ''),
        ('latin_1', 'latin_1', ''),
        ('shift_jis', 'shift_jis', ''),
        ]

    return cp_list


def load_translate() -> Dict[str, Dict[Tuple[str, str], str]] :
    translation_dict = {
        'en_US' : {
            ('*', 'Import Normals') : 'Import Normals',
            ('*', 'Import vertex normals (split normals)'): 'Import vertex normals (split normals)',
            ('*', 'Import animation') : 'Import animation',
            ('*', 'Import skeletal animations as actions') : 'Import skeletal animations as actions',
            ('*', 'Adjust frame rate') : 'Adjust frame rate',
            ('*', 'Adjust scene frame rate to match imported animation') : 'Adjust scene frame rate to match imported animation',
            ('*', 'Import shape keys') : 'Import shape keys',
            ('*', 'Import shape keys (morphs)') : 'Import shape keys (morphs)',
            ('*', 'Create materials') : 'Create materials',
            ('*', 'Create materials (name only)') : 'Create materials (name only)',
            ('*', 'Use selected armature') : 'Use selected armature',
            ('*', '''Link with selected armature when importing mesh.
skeleton is not imported.
Use this when importing gear meshes that don't have their own skeleton.
Make sure the correct armature is selected.
Weightmaps can get mixed up if not selected''')
                : '''Link with selected armature when importing mesh.
skeleton is not imported.
Use this when importing gear meshes that don't have their own skeleton.
Make sure the correct armature is selected.
Weightmaps can get mixed up if not selected''',
            ('*', 'Encoding') : 'Encoding',
            ('*', 'If characters are not displayed correctly, try changing the character code') : 'If characters are not displayed correctly, try changing the character code',
            ('*', 'Mesh version') : 'Mesh version',
            ('*', 'The latest version that supports Kenshi') : 'The latest version that supports Kenshi',
            ('*', 'Particle Universe Editor compatible version'): 'Particle Universe Editor compatible version',
            ('*', 'Scythe Physics Editor compatible version') : 'Scythe Physics Editor compatible version',
            ('*', 'Tangent format') : 'Tangent format',
            ('*', 'tangent & binormal') : 'tangent & binormal',
            ('*', 'Export tangent and binormal.') : 'Export tangent and binormal.',
            ('*', 'tangent & binormal & sign') : 'tangent & binormal & sign',
            ('*', 'Export tangent and bitangent\'s signs and binormal (before multiplying by sign).') : 'Export tangent and bitangent\'s signs and binormal (before multiplying by sign).',
            ('*', 'tangent & bitangent sign') : 'tangent & bitangent sign',
            ('*', 'Export tangent and bitangent\'s signs.\nCompute the binormals at runtime.') : 'Export tangent and bitangent\'s signs.\nCompute the binormals at runtime.',
            ('*', 'no tangent') : 'no tangent',
            ('*', 'Select if there is no UV map.') : 'Select if there is no UV map.',
            ('*', 'Export vertex colour') : 'Export vertex colour',
            ('*', "Export vertex colour data.\nName a colour layer 'Alpha' to use as the alpha component") : "Export vertex colour data.\nName a colour layer 'Alpha' to use as the alpha component",
            ('*', 'Apply Transform') : 'Apply Transform',
            ('*', "Applies object's transformation to its data") : "Applies object's transformation to its data",
            ('*', 'Apply Modifiers') : 'Apply Modifiers',
            ('*', 'Applies modifiers to the mesh'): 'Applies modifiers to the mesh',
            ('*', 'Export shape keys') : 'Export shape keys',
            ('*', 'Export shape keys as poses') : 'Export shape keys as poses',
            ('*', 'Export shape normals') : 'xport shape normals',
            ('*', 'Include shape normals') : 'Include shape normals',
            ('*', 'Optimize mesh') : 'Optimize mesh',
            ('*', 'Remove duplicate vertices.\nThe conditions for duplication are that they have the same position, normal, tangent, bitangent, texture coordinates, and color')
                : 'Remove duplicate vertices.\nThe conditions for duplication are that they have the same position, normal, tangent, bitangent, texture coordinates, and color',
            ('*', 'Export skeleton') : 'Export skeleton',
            ('*', 'Exports new skeleton and links the mesh to this new skeleton.\nLeave off to link with existing skeleton if applicable.')
                : 'Exports new skeleton and links the mesh to this new skeleton.\nLeave off to link with existing skeleton if applicable.',
            ('*', 'Export Animation') : 'Export Animation',
            ('*', 'Export all actions attached to the selected skeleton as animations') : 'Export all actions attached to the selected skeleton as animations',
            ('*', 'Include bones with undefined IDs') : 'Include bones with undefined IDs',
            ('*', 'Export all bones.\nVertex weights and skeletal animation are also covered.') : 'Export all bones.\nVertex weights and skeletal animation are also covered.',
            ('*', 'Objects') : 'Objects',
            ('*', 'Which objects to export') : 'Which objects to export',
            ('*', 'All Objects') : 'All Objects',
            ('*', 'Export all collision objects in the scene') : 'Export all collision objects in the scene',
            ('*', 'Selection') : 'Selection',
            ('*', 'Export only selected objects') : 'Export only selected objects',
            ('*', 'Selected Children') : 'Selected Children',
            ('*', 'Export selected objects and all their child objects') : 'Export selected objects and all their child objects',
            ('*', 'Transform') : 'Transform',
            ('*', 'Scene') : 'Scene',
            ('*', 'Export objects relative to scene origin') : 'Export objects relative to scene origin',
            ('*', 'Parent') : 'Parent',
            ('*', 'Export objects relative to common parent') : 'Export objects relative to common parent',
            ('*', 'Active') : 'Active',
            ('*', 'Export objects relative to the active object') : 'Export objects relative to the active object',
            ('*', 'Link animation to selected armature object') : 'Link animation to selected armature object',
            ('*', 'Skeleton version') : 'Skeleton version',
            ('*', 'Determine mesh name from file name') : 'Determine mesh name from file name',
            ('*', "mesh name will be 'filename_number'") : "mesh name will be 'filename_number'",
            ('*', 'Failed to decode submesh name, replaced with default name.') : 'Failed to decode submesh name, replaced with default name.',
            ('*', 'Failed to decode material name, replaced with default name.') : 'Failed to decode material name, replaced with default name.',
            ('*', 'Selected armature has no OGRE data') : 'Selected armature has no OGRE data',
            ('*', 'Failed to load linked skeleton') : 'Failed to load linked skeleton',
            ('*', 'No objects selected for export') : 'No objects selected for export',
            ('*', 'Selected file is not exist') : 'Selected file is not exist',
            ('*', 'Import successful') : 'Import successful',
            ('*', 'Export successful') : 'Export successful',
            ('*', 'Set scale keyframes in the animation') : 'Set scale keyframes in the animation',
            ('*', 'Apply scale') : 'Apply scale',
            ('*', '''Set keyframes based on visuals.
More frames will slow down the export,
so it's a good idea to pre-bake the animation and uncheck this option''')
            : '''Set keyframes based on visuals.
More frames will slow down the export,
so it's a good idea to pre-bake the animation and uncheck this option''',
            ('*', "Canceled because 'use selected armature' A is enabled and 'Import animation' is disabled") : "Canceled because 'use selected armature' A is enabled and 'Import animation' is disabled",
        },
        'ja_JP' : {
            ('*', 'Import Normals') : '法線をインポート',
            ('*', 'Import vertex normals (split normals)') : '頂点法線(分割法線)をインポートします',
            ('*', 'Import animation') : 'アニメーションをインポート',
            ('*', 'Import skeletal animations as actions') : 'スケルタルアニメーションをアクションとしてインポートします',
            ('*', 'Adjust frame rate') : 'フレームレートを調整',
            ('*', 'Adjust scene frame rate to match imported animation') : 'インポートしたアニメーションに合わせてシーンのフレームレートを調整します',
            ('*', 'Import shape keys') : 'シェイプキーをインポート',
            ('*', 'Import shape keys (morphs)') : 'シェイプキー(モーフ)をインポートします',
            ('*', 'Create materials') : 'マテリアルを作成',
            ('*', 'Create materials (name only)') : 'マテリアルを作成します(名前のみ)',
            ('*', 'Use selected armature') : '選択したアーマチュアを使用',
            ('*', '''Link with selected armature when importing mesh.
skeleton is not imported.
Use this when importing gear meshes that don't have their own skeleton.
Make sure the correct armature is selected.
Weightmaps can get mixed up if not selected''')
            : '''メッシュのインポート時に選択したアーマチュアとリンクします
スケルトンはインポートされません
独自のスケルトンを持たない装備のメッシュをインポートする場合にこれを使用します
正しいアーマチュアが選択されていることを確認してください
選択されていないと、ウェイトマップが混同される可能性があります''',
            ('*', 'Encoding') : 'エンコーディング',
            ('*', 'If characters are not displayed correctly, try changing the character code') : '文字が正常に表示されない場合は、文字コードを変更してみてください',
            ('*', 'Mesh version') : 'メッシュバージョン',
            ('*', 'The latest version that supports Kenshi') : 'Kenshi に対応している最新のバージョン',
            ('*', 'Particle Universe Editor compatible version') : 'Particle Universe Editor 互換バージョン',
            ('*', 'Scythe Physics Editor compatible version') : 'Scythe Physics Editor 互換バージョン',
            ('*', 'Tangent format') : '接線のフォーマット',
            ('*', 'tangent & binormal') : '接線と従法線',
            ('*', 'Export tangent and binormal.') : '接線と従法線をエクスポートします',
            ('*', 'tangent & binormal & sign') : '接線と従法線と従接線の符号',
            ('*', 'Export tangent and bitangent\'s signs and binormal (before multiplying by sign).') : '接線と従接線の符号と従法線(符号乗算前)をエクスポートします',
            ('*', 'tangent & bitangent sign') : '接線と従接線の符号',
            ('*', 'Export tangent and bitangent\'s signs.\nCompute the binormals at runtime.') : '接線と従接線の符号をエクスポートします\n実行時に従法線を計算します',
            ('*', 'no tangent') : '接線なし',
            ('*', 'Select if there is no UV map.') : 'UVマップがない場合に選択します',
            ('*', 'Export vertex colour') : '頂点カラーをエクスポート',
            ('*', "Export vertex colour data.\nName a colour layer 'Alpha' to use as the alpha component") : '頂点カラーデータをエクスポートします\nアルファ成分として使用するカラーレイヤーに「Alpha」という名前を付けます',
            ('*', 'Apply Transform') : 'トランスフォームを適用',
            ('*', "Applies object's transformation to its data") : 'オブジェクトのトランスフォームを適用します',
            ('*', 'Apply Modifiers') : 'モディファイアを適用',
            ('*', 'Applies modifiers to the mesh') : 'メッシュのモディファイアを適用します',
            ('*', 'Export shape keys') : 'シェイプキーをエクスポート',
            ('*', 'Export shape keys as poses') : 'シェイプキーをポーズとしてエクスポートします',
            ('*', 'Export shape normals') : 'シェイプノーマルをエクスポート',
            ('*', 'Include shape normals') : 'シェイプノーマルを含める',
            ('*', 'Optimize mesh') : 'メッシュを最適化',
            ('*', 'Remove duplicate vertices.\nThe conditions for duplication are that they have the same position, normal, tangent, bitangent, texture coordinates, and color')
                : '重複した頂点を削除します\n重複の条件は、位置、法線、接線、従接線、テクスチャ座標、色が同じであることです',
            ('*', 'Export skeleton') : 'スケルトンをエクスポート',
            ('*', 'Exports new skeleton and links the mesh to this new skeleton.\nLeave off to link with existing skeleton if applicable.')
                : '新しいスケルトンをエクスポートし、メッシュをこの新しいスケルトンにリンクします\n既存のスケルトンとリンクする場合はオフのままにします',
            ('*', 'Export Animation') : 'アニメーションをエクスポート',
            ('*', 'Export all actions attached to the selected skeleton as animations') : '選択したスケルトンにアタッチされているすべてのアクションをアニメーションとしてエクスポートします',
            ('*', 'Include bones with undefined IDs') : 'IDが未定義のボーンを含める',
            ('*', 'Export all bones.\nVertex weights and skeletal animation are also covered.') : 'すべてのボーンをエクスポートします\n頂点ウェイトとスケルタルアニメーションも対象です',
            ('*', 'Objects') : 'オブジェクト',
            ('*', 'Which objects to export') : 'どのオブジェクトをエクスポートするか',
            ('*', 'All Objects') : '全オブジェクト',
            ('*', 'Export all collision objects in the scene') : 'シーン内のすべてのコリジョンオブジェクトをエクスポートします',
            ('*', 'Selection') : '選択',
            ('*', 'Export only selected objects') : '選択したオブジェクトのみをエクスポートします',
            ('*', 'Selected Children') : '選択(子を含む)',
            ('*', 'Export selected objects and all their child objects') : '選択したオブジェクトとそのすべての子オブジェクトをエクスポートします',
            ('*', 'Transform') : 'トランスフォーム',
            ('*', 'Scene') : 'シーン',
            ('*', 'Export objects relative to scene origin') : 'シーンの原点を基準にオブジェクトをエクスポートします',
            ('*', 'Parent') : 'ペアレント',
            ('*', 'Export objects relative to common parent') : '共通のペアレントを基準にオブジェクトをエクスポートします',
            ('*', 'Active') : 'アクティブ',
            ('*', 'Export objects relative to the active object') : 'アクティブなオブジェクトを基準にオブジェクトをエクスポートします',
            ('*', 'Link animation to selected armature object') : '選択したアーマチュアオブジェクトにアニメーションをリンクします',
            ('*', 'Skeleton version') : 'スケルトンバージョン',
            ('*', 'Determine mesh name from file name') : 'ファイル名からメッシュ名を決定',
            ('*', "mesh name will be 'filename_number'") : "メッシュ名が「ファイル名_番号」になります",
            ('*', 'Failed to decode submesh name, replaced with default name.') : 'メッシュ名のデコードに失敗したので、デフォルト名に置き換えました',
            ('*', 'Failed to decode material name, replaced with default name.') : 'マテリアル名のデコードに失敗したので、デフォルト名に置き換えました',
            ('*', 'Selected armature has no OGRE data') : '選択したアーマチュアにはOGREデータがありません',
            ('*', 'Failed to load linked skeleton') : 'リンクされたスケルトンの読み込みに失敗しました',
            ('*', 'No objects selected for export') : 'エクスポートするオブジェクトが選択されていません',
            ('*', 'Selected file is not exist') : '選択したファイルは存在しません',
            ('*', 'Import successful') : 'インポート成功',
            ('*', 'Export successful') : 'エクスポート成功',
            ('*', 'Set scale keyframes in the animation') : 'アニメーションにスケールのキーフレームを設定します',
            ('*', 'Apply scale') : 'スケールを適用',
            ('*', '''Set keyframes based on visuals.
More frames will slow down the export,
so it's a good idea to pre-bake the animation and uncheck this option''')
            : '''ビジュアルに基づいてキーフレームを設定します
フレーム数が増えるとエクスポートが遅くなるので、
事前にアニメーションをベイクしてこのオプションをオフにすることをお勧めします''',
            ('*', "Canceled because 'use selected armature' A is enabled and 'Import animation' is disabled") : "「選択したアーマチュアを使用」が有効で「アニメーションをインポート」が無効になっているため、キャンセルされました",
        }
    }

    return translation_dict