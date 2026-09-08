# ウィジェットの View はアプリのモジュールに無いので、`@testable import` では見えない。
# 拡張ターゲット専用のソースを**テスト側に足す**（アプリと共有しているファイルは既に見えるので足さない）。
# `@main` は消した写しを使う（テストの中に @main は置けない）。
if widget_src_dir && !widget_src_dir.empty?
  app_files = app.source_build_phase.files.map { |f| f.file_ref&.real_path.to_s }.compact
  # 拡張のうち iOS 向けのものだけ。watchOS の拡張を混ぜると、iOS に無いウィジェット
  # ファミリ（accessoryCorner 等）を参照してビルドごと落ちる
  ios_ext = lambda do |t|
    next true unless t.respond_to?(:build_configurations)
    v = t.build_configurations.map { |c|
      "#{c.build_settings['SDKROOT']} #{c.build_settings['SUPPORTED_PLATFORMS']}"
    }.join(' ').strip
    v.empty? || v.include?('iphoneos') || v.include?('auto')
  end
  exts = proj_orig.targets.select { |t| t.respond_to?(:product_type) &&
    t.product_type.to_s.include?('app-extension') && ios_ext.call(t) }
  require 'fileutils'
  FileUtils.mkdir_p(widget_src_dir)
  added = []
  exts.each do |t|
    next unless t.respond_to?(:source_build_phase)
    t.source_build_phase.files.each do |bf|
      path = bf.file_ref&.real_path.to_s
      next if path.empty? || !path.end_with?('.swift') || app_files.include?(path)
      text = File.read(path)
      # ウィジェット本体（@main / WidgetBundle）は焼くのに要らない
      text = text.gsub(/^@main\s*$/, '// [bakeshot] @main はテストに置けないので外しました')
      # 拡張のファイルはアプリの型（Shared/ の Station 等）を使う。テスト側では @testable でしか見えない
      text = "@testable import #{host.gsub('-', '_')}\n" + text
      # ウィジェットの環境値はホストが与えるもので、外から渡せない。
      # 保存プロパティに直して、台本から family を指定できるようにする（private も外す）
      text = text.gsub(/^([ \t]*)@Environment\(\\\.widgetFamily\)[ \t]+(?:private[ \t]+)?var[ \t]+(\w+)[ \t]*$/,
                       '\\1var \\2: WidgetFamily = .systemMedium   // [bakeshot] 台本から渡せるようにした')
      text = text.gsub(/^([ \t]*)@Environment\(\\\.widgetRenderingMode\)[ \t]+(?:private[ \t]+)?var[ \t]+(\w+)[ \t]*$/,
                       '\\1var \\2: WidgetRenderingMode = .fullColor   // [bakeshot] 台本から渡せるようにした')
      dst_file = File.join(widget_src_dir, File.basename(path))
      next if added.include?(dst_file)
      File.write(dst_file, text)
      added << dst_file
    end
  end
  refs2 = added.map { |f| group.new_file(f) }
  test.add_file_references(refs2)
  puts "widget-sources: #{added.size}"
end

