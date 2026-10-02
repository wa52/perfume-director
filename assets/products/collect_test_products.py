"""Acquire an auditable 15-product test set from public original packshots.

No segmentation, recolouring or generated product imagery is used. A source
image without actual transparent pixels is rejected instead of being labelled
as a cutout. Run from any directory; existing images are verified and reused.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCTS = [
    ("prada-paradoxe", "Prada", "Paradoxe", "Prada-Paradoxe-Eau-de-Parfum-90ml/SW10250.2", "三角形透明瓶、黑色侧盖，宽轮廓与留白协调", "floral_amber"),
    ("mugler-angel", "Mugler", "Angel", "Thierry-Mugler-Angel-Eau-de-Parfum-50ml/SW10267", "蓝色透明星形瓶、尖角与镜面金属，非矩形接地", "gourmand"),
    ("carolina-herrera-very-good-girl", "Carolina Herrera", "Very Good Girl", "Carolina-Herrera-Very-Good-Girl-Eau-de-Parfum-50ml/SW10152", "红色高跟鞋造型、细金属鞋跟，非单点接地", "fruity_floral"),
    ("bvlgari-omnia-crystalline", "Bvlgari", "Omnia Crystalline", "Bvlgari-Omnia-Crystalline-Woman-Eau-de-Toilette-40ml/BVL-00001", "双环银色透明瓶、内部镂空与高反光", "floral_woody"),
    ("gucci-flora-gorgeous-jasmine", "Gucci", "Flora Gorgeous Jasmine", "Gucci-Flora-Gorgeous-Jasmine-Eau-de-Parfum-100ml/SW10249.2", "青绿色不透明细长瓶、繁复花纹标签与大黑盖", "white_floral"),
    ("guerlain-shalimar", "Guerlain", "Shalimar", "Guerlain-Shalimar-Eau-de-Parfum-90ml/SW10313", "扇形蓝色大盖、宽玻璃瓶、金色液体和小底座", "amber_vanilla"),
    ("hermes-terre", "Hermès", "Terre d’Hermès", "Hermes-Terre-d-Hermes-Eau-de-Toilette-100ml/SW10236.1", "棕色透明直角瓶、黑橙底部、边缘反射与小字", "woody_citrus"),
    ("davidoff-cool-water", "Davidoff", "Cool Water", "Davidoff-Cool-Water-Men-Eau-de-Toilette-125ml/DAV-00008.1", "细长深蓝透明瓶、小金色字标与深色底部", "aromatic_aquatic"),
    ("kenzo-jungle", "Kenzo", "Jungle", "Kenzo-Jungle-Eau-de-Parfum-30ml/SW10154", "金色象形雕塑瓶盖、琥珀圆肩瓶，轮廓细节复杂", "spicy_amber"),
    ("chloe-eau-de-parfum", "Chloé", "Chloé", "Chloe-Chloe-Eau-de-Parfum-50ml/CHL-00001.1", "米色丝带、银色肩部、透明竖纹玻璃及浅色液体", "rose_floral"),
    ("versace-yellow-diamond-intense", "Versace", "Yellow Diamond Intense", "Versace-Yellow-Diamond-Intense-Eau-de-Parfum-30-ml/SW10705", "超宽钻石切面瓶盖、黄色透明玻璃、高亮边缘", "citrus_floral"),
    ("narciso-rodriguez-poudree", "Narciso Rodriguez", "Narciso Poudrée", "Narciso-Rodriguez-Narciso-Poudree-Eau-de-Parfum-90ml/SW10259", "浅粉方形磨砂内胆、低对比边缘与同色立方瓶盖", "powdery_musk"),
    ("guerlain-mandarine-basilic", "Guerlain", "Aqua Allegoria Mandarine Basilic", "Guerlain-Aqua-Allegoria-Mandarine-Basilic-Eau-de-Toilette-75ml/SW10261", "蜂窝金属笼罩、金色球盖、透明圆柱瓶", "citrus_aromatic"),
]


def get(url, referer=None):
    # Source HTML can contain spaces in media URLs; quote only URL path.
    split = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit((split.scheme, split.netloc,
        urllib.parse.quote(urllib.parse.unquote(split.path), safe="/"), split.query, split.fragment))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": referer or url})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = response.read(20_000_001)
    if len(data) > 20_000_000:
        raise ValueError("Source file exceeds 20 MB")
    return data, url


def inspect_image(path):
    content = path.read_bytes()
    with Image.open(io.BytesIO(content)) as im:
        im.load()
        alpha = im.getchannel("A") if "A" in im.getbands() else None
        if min(im.size) < 500 or alpha is None or alpha.getextrema() != (0, 255):
            raise ValueError("Product requires >=500 px and a genuine transparent alpha channel")
        hist = alpha.histogram()
        opaque = sum(hist[240:]) / (im.width * im.height)
        transparent = hist[0] / (im.width * im.height)
        if transparent < 0.05 or opaque < 0.01:
            raise ValueError("Alpha channel does not contain a usable cutout")
        return dict(width=im.width, height=im.height, mode=im.mode,
                    format=im.format, alpha_extrema=list(alpha.getextrema()),
                    alpha_bbox=list(alpha.getbbox()),
                    transparent_fraction=round(transparent, 5),
                    opaque_fraction=round(opaque, 5),
                    sha256=hashlib.sha256(content).hexdigest(),
                    local_path=path.relative_to(ROOT).as_posix(),
                    image_processing="none; original source bytes",
                    usable=True)


def acquire(item):
    slug, brand, name, suffix, challenge, fragrance_position = item
    source = "https://mondo-parfum.de/" + suffix
    page_bytes, _ = get(source)
    page = page_bytes.decode("utf-8")
    match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', page)
    if not match:
        raise ValueError("Source has no og:image")
    image_url = html.unescape(match.group(1))
    content, image_url = get(image_url, source)
    path = HERE / (slug + "-retailer.png")
    path.write_bytes(content)
    metrics = inspect_image(path)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    text = re.sub(r"\s+", " ", text)
    # A bounded source excerpt is retained for checking our coverage labels.
    start = text.find("Produktinformationen")
    excerpt = text[start:start + 3000] if start >= 0 else ""
    record = dict(id=slug, brand=brand, name=name, source_url=source,
        image_url=image_url, visual_challenges=challenge,
        fragrance_position=fragrance_position,
        fragrance_position_status="coarse test-coverage label; verify against linked retailer description",
        brief=f"为 {brand} {name} 制作高品质商业香水海报。保留上传商品原貌与可见标签；为这款商品形成四个真正不同的创意方向。只使用品牌与产品名称，不添加价格、容量、促销、新品或功效宣传。",
        approved_copy={"logo": brand, "title": name, "subtitle": "", "price": ""},
        rights_status="original_rights_retained; commercial_reuse_unverified",
        acquired_at=datetime.now(timezone.utc).isoformat(), **metrics)
    return record, {"id": slug, "source_url": source, "source_excerpt": excerpt}


def contact_sheet(records):
    canvas = Image.new("RGB", (1500, 1530), "#ededed")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    for n, record in enumerate(records):
        x, y = (n % 5) * 300, (n // 5) * 510
        draw.rectangle((x+8, y+8, x+292, y+456), fill="#34434d" if n % 2 else "#ddd4c7")
        with Image.open(ROOT / record["local_path"]) as source:
            im = source.convert("RGBA")
            im = im.crop(im.getchannel("A").getbbox())
            im.thumbnail((255, 420), Image.Resampling.LANCZOS)
            canvas.paste(im, (x+(300-im.width)//2, y+20+(425-im.height)//2), im)
        draw.text((x+12, y+466), str(n+1)+". "+record["brand"], fill="black", font=font)
        name = record["name"]
        draw.text((x+12, y+490), name[:31], fill="black", font=font)
    canvas.save(HERE / "test-products-15-contact.jpg", quality=93)


def main():
    existing = json.loads((HERE / "sources.json").read_text("utf-8"))
    records = []
    for index, (slug, brand, name, challenge, position) in enumerate([
        ("dior-jadore", "Dior", "J’adore", "细长金色瓶颈、圆形透明瓶腹，窄轮廓和金属反射", "floral"),
        ("tom-ford-tobacco-vanille", "Tom Ford", "Tobacco Vanille", "深棕不透明直角瓶、金色边框标签，暗部识别与接触阴影", "tobacco_vanilla"),
    ]):
        source = existing[index]
        records.append(dict(id=slug, brand=brand, name=name,
            source_url=source["source_url"], image_url=source["image_url"],
            visual_challenges=challenge, fragrance_position=position,
            fragrance_position_status="coarse test-coverage label; linked retailer description",
            brief=f"为 {brand} {name} 制作高品质商业香水海报。保留上传商品原貌与可见标签；为这款商品形成四个真正不同的创意方向。只使用品牌与产品名称，不添加价格、容量、促销、新品或功效宣传。",
            approved_copy={"logo": brand, "title": name, "subtitle": "", "price": ""},
            rights_status=source["rights_status"], **inspect_image(ROOT/source["local_path"])))
    by_id = {r["id"]: r for r in records}
    excerpts, errors = [], []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(acquire, item): item[0] for item in PRODUCTS}
        for future in as_completed(futures):
            try:
                record, excerpt = future.result()
                by_id[record["id"]] = record
                excerpts.append(excerpt)
                print(json.dumps({"id": record["id"], "status": "verified", "alpha_bbox": record["alpha_bbox"]}), flush=True)
            except Exception as error:
                errors.append({"id": futures[future], "error": str(error)})
                print(json.dumps(errors[-1]), flush=True)
            ordered = [by_id[x] for x in ["dior-jadore", "tom-ford-tobacco-vanille"] + [i[0] for i in PRODUCTS] if x in by_id]
            (HERE/"test-products-15.json").write_text(json.dumps({
                "schema_version": 1, "target_count": 15, "count": len(ordered),
                "products": ordered, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE/"test-products-source-excerpts.json").write_text(json.dumps(excerpts, ensure_ascii=False, indent=2), encoding="utf-8")
    contact_sheet(ordered)
    if len(ordered) != 15:
        raise SystemExit(f"Acquired {len(ordered)}/15; see manifest errors")


if __name__ == "__main__":
    main()
