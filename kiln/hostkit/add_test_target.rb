# Kiln: 焼きたいアプリの .xcodeproj を複製し、アプリをホストにした XCTest ターゲットを足す。
# 使い方: ruby add_test_target.rb <src.xcodeproj> <dst.xcodeproj> <sources(":"区切り)> <appTarget>
#           [bundleIdOverride] [stripExtensions 0/1] [stripEntitlements 0/1] [language] [team]
require 'xcodeproj'
require 'fileutils'
src, dst, test_srcs, host, bundle_override, strip_ext, strip_ent, lang, team, widget_src_dir = ARGV
FileUtils.rm_rf(dst); FileUtils.cp_r(src, dst)
proj = Xcodeproj::Project.open(dst)
# 拡張は複製から外すので、拡張のソース一覧は**元のプロジェクト**から読む
proj_orig = Xcodeproj::Project.open(src)
app = proj.targets.find { |t| t.name == host } or abort("no target #{host}")

# 署名するチームは、**そのプロジェクトが既に持っているもの**を使う。
# （買い手は自分のアプリを焼くので、必ず入っている。無ければ xcconfig からも探す）
if team.nil? || team.empty?
  team = app.build_configurations.map { |c| c.build_settings['DEVELOPMENT_TEAM'] }.compact.first
  team ||= proj.build_configurations.map { |c| c.build_settings['DEVELOPMENT_TEAM'] }.compact.first
  if team.nil? || team.empty? || team.include?('$(')
    Dir.glob(File.join(File.dirname(src), '*.xcconfig')).each do |f|
      m = File.read(f)[/^\s*DEVELOPMENT_TEAM\s*=\s*(\S+)/, 1]
      team = m if m && !m.include?('$(')
      break if team && !team.empty?
    end
  end
end
if team.nil? || team.empty? || team.include?('$(')
  abort("署名するチームが分かりません。Xcode でアプリのターゲットに Team を設定するか、`kiln bake --team <ID>` で渡してください。")
end

dt = (app.build_configurations.map { |c| c.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] } +
      proj.build_configurations.map { |c| c.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] }).compact.first || '17.0'
test = proj.new_target(:unit_test_bundle, 'KilnRenderTests', :ios, dt)
group = proj.main_group.new_group('KilnRender')
refs = test_srcs.split(':').reject(&:empty?).map { |f| group.new_file(f) }
test.add_file_references(refs)
test.add_dependency(app)

# 拡張（ウィジェット・通知・共有）はスクショに要らない。署名の手間と失敗の元なので複製から外す
if strip_ext == '1'
  removed = proj.targets.select do |t|
    t != app && t != test && t.respond_to?(:product_type) &&
      !t.product_type.to_s.start_with?('com.apple.product-type.application')
  end
  removed_refs = removed.map { |t| t.product_reference }.compact
  app.dependencies.dup.each { |d| d.remove_from_project if d.target && removed.include?(d.target) }
  app.build_phases.each do |ph|
    next unless ph.respond_to?(:files)
    ph.files.dup.each { |bf| bf.remove_from_project if bf.file_ref && removed_refs.include?(bf.file_ref) }
  end
  # Xcode 16 の「同期フォルダ」は、ターゲットごとの例外セットを持つ。消すターゲットを指すものを先に外す
  # （残すと保存時に nil.name で落ちる）
  proj.objects.select { |o| o.isa == 'PBXFileSystemSynchronizedBuildFileExceptionSet' }.each do |ex|
    next unless ex.respond_to?(:target) && removed.include?(ex.target)
    proj.objects.select { |o| o.isa == 'PBXFileSystemSynchronizedRootGroup' }.each do |g|
      g.exceptions.delete(ex) if g.respond_to?(:exceptions) && g.exceptions
    end
    ex.remove_from_project
  end
  removed.each { |t| t.remove_from_project }
end

# ウィジェットの View はアプリのモジュールに無いので、`@testable import` では見えない。
# 拡張ターゲット専用のソースを**テスト側に足す**（アプリと共有しているファイルは既に見えるので足さない）。
# `@main` は消した写しを使う（テストの中に @main は置けない）。
if widget_src_dir && !widget_src_dir.empty?
  app_files = app.source_build_phase.files.map { |f| f.file_ref&.real_path.to_s }.compact
  exts = proj_orig.targets.select { |t| t.respond_to?(:product_type) &&
    t.product_type.to_s.include?('app-extension') }
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
      text = text.gsub(/^@main\s*$/, '// [kiln] @main はテストに置けないので外しました')
      # 拡張のファイルはアプリの型（Shared/ の Station 等）を使う。テスト側では @testable でしか見えない
      text = "@testable import #{host.gsub('-', '_')}\n" + text
      # ウィジェットの環境値はホストが与えるもので、外から渡せない。
      # 保存プロパティに直して、台本から family を指定できるようにする（private も外す）
      text = text.gsub(/^([ \t]*)@Environment\(\\\.widgetFamily\)[ \t]+(?:private[ \t]+)?var[ \t]+(\w+)[ \t]*$/,
                       '\\1var \\2: WidgetFamily = .systemMedium   // [kiln] 台本から渡せるようにした')
      text = text.gsub(/^([ \t]*)@Environment\(\\\.widgetRenderingMode\)[ \t]+(?:private[ \t]+)?var[ \t]+(\w+)[ \t]*$/,
                       '\\1var \\2: WidgetRenderingMode = .fullColor   // [kiln] 台本から渡せるようにした')
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

test.build_configurations.each do |c|
  s = c.build_settings
  # 製品名はターゲット名と違うことがある（IceCubesApp → "Ice Cubes.app"）。空白があると xcodebuild がホストを見失う
  prod = app.product_reference ? File.basename(app.product_reference.path, '.app') : host
  if prod.include?(' ')
    prod = host
    app.build_configurations.each { |ac| ac.build_settings['PRODUCT_NAME'] = host }
    app.product_reference.path = "#{host}.app" if app.product_reference
  end
  s['TEST_HOST'] = "$(BUILT_PRODUCTS_DIR)/#{prod}.app/#{prod}"
  s['BUNDLE_LOADER'] = '$(TEST_HOST)'
  s['PRODUCT_BUNDLE_IDENTIFIER'] = 'com.artemis.kiln.rendertests'
  s['PRODUCT_NAME'] = 'KilnRenderTests'
  s['DEVELOPMENT_TEAM'] = team
  s['CODE_SIGN_STYLE'] = 'Automatic'
  s['GENERATE_INFOPLIST_FILE'] = 'YES'
  s['SWIFT_VERSION'] = '5.0'
  s['TARGETED_DEVICE_FAMILY'] = '1,2'
  s['SUPPORTED_PLATFORMS'] = 'iphoneos iphonesimulator'
  s['IPHONEOS_DEPLOYMENT_TARGET'] = dt
  s['SUPPORTS_MACCATALYST'] = 'NO'
  s['SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD'] = 'YES'
end

app.build_configurations.each do |c|
  c.build_settings['PRODUCT_BUNDLE_IDENTIFIER'] = bundle_override if bundle_override && !bundle_override.empty?
  c.build_settings['CODE_SIGN_ENTITLEMENTS'] = '' if strip_ent == '1'
  c.build_settings['CURRENT_PROJECT_VERSION'] ||= '1'
  c.build_settings['MARKETING_VERSION'] ||= '1.0'
end
# My Mac (Designed for iPad) で動かす。Catalyst / visionOS 側に倒れると拡張と食い違って host が見つからない
proj.targets.each do |t|
  next unless t.respond_to?(:build_configurations)
  t.build_configurations.each do |c|
    c.build_settings['SUPPORTS_MACCATALYST'] = 'NO'
    c.build_settings['SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD'] = 'YES'
    c.build_settings['SUPPORTED_PLATFORMS'] = 'iphoneos iphonesimulator' if c.build_settings['SUPPORTED_PLATFORMS']
    # マルチプラットフォーム設定（SDKROOT=auto / visionOS の device family 7）だとテストホストが解決できない
    c.build_settings['SDKROOT'] = 'iphoneos' if c.build_settings['SDKROOT'].to_s == 'auto'
    fam = c.build_settings['TARGETED_DEVICE_FAMILY'].to_s
    c.build_settings['TARGETED_DEVICE_FAMILY'] = '1,2' if fam.include?('7')
    c.build_settings['DEVELOPMENT_TEAM'] = team
    c.build_settings['CODE_SIGN_STYLE'] = 'Automatic'
  end
end
proj.save

scheme = Xcodeproj::XCScheme.new
scheme.add_build_target(app)
scheme.add_build_target(test, false)
scheme.add_test_target(test)
if lang && !lang.empty?
  # アプリの言語。テスト実行時の Application Language に相当する
  scheme.test_action.xml_element.attributes['language'] = lang
  scheme.launch_action.xml_element.attributes['language'] = lang
end
scheme.save_as(dst, 'KilnRender', true)
puts "ok: #{dst}"
