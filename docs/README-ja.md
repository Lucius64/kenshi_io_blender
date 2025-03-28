# Kenshi Blender Plugin

[English](README.md)

Kenshiの3DアセットをBlenderにインポート及びエクスポートするためのプラグインです。


## 要件

- Windows
- Blender 2.79以上


## 機能
以下のオペレーターがあります。

- meshのインポート
- meshのエクスポート
- skeletonのインポート
- skeletonのエクスポート
- コリジョン(xmlファイル)のインポート
- コリジョン(xmlファイル)のエクスポート


## 説明

- [インストール/アンインストール方法](Installation_extension-ja.md)
    - [旧アドオン](Installation-ja.md)
- [オプションの説明](Option_description-ja.md)


## 改善点

### パフォーマンス

パフォーマンスが向上し、より高速に動作するようになりました。

参考までにBlender 2.93における「human_male.mesh」と「male_skeleton.skeleton」の処理時間は以下の通りです。

| 条件 | インポート | エクスポート |
| --- | --------- | ----------- |
| メッシュのみ | 約5.5s → 0.233s | 約7.2s → 0.074s |
| スケルトン含む | 約24.5s → 0.254s | 約7.3s → 0.075s |
| アニメーション含む | 約34.5s → 0.861s | 約50s → 0.925s |


### 不具合修正

公式版に存在する以下のバグを修正しています。
- メッシュとスケルトンをインポートするとメモリリークする
- インポートオペレーターのUNDOが機能しない
- 上記が原因で一部のバージョンでUNDO時にクラッシュする
- コリジョンエクスポートにおける多数の不具合
- 凸包コリジョンがゲーム内で生成できない
- バニラの男性アニメーションをインポートする際に#INFと#INDが原因で一部のキーフレームが欠落する
- 公式版0.9.0以降、アルファチャンネル用の頂点カラーが正しくインポート出来ない
- 公式版0.9.0以降、UVマップがなく、頂点カラーがあるメッシュのインポートが失敗する
- 公式版0.9.0以降、インポートしたメッシュにスムーズシェードが適用されない
- 複数のアニメーションをエクスポートする際、キーフレームの無いボーンが直前のアニメーションのポーズを引き継いでしまう
- Blender 2.92以下でオブジェクト名やマテリアル名に非ASCII文字を含むモデルをエクスポートすると異なる地域のユーザーやBlender 2.93以上でインポートが失敗する


## NOTICE

[NOTICE](NOTICE.md)
