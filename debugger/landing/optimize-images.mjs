import sharp from "sharp"
import { readdirSync, mkdirSync } from "fs"
import { join, basename, extname } from "path"

const input = "./images"
const output = "./public/images"

mkdirSync(output, { recursive: true })

const files = readdirSync(input).filter(f => extname(f) === ".png")

for (const file of files) {
  const name = basename(file, ".png")
  const meta = await sharp(join(input, file)).metadata()
  const w = meta.width ?? 1200
  const h = meta.height ?? 768
  // crop 90px off bottom to fully remove Gemini watermark
  const cropHeight = h - 90
  await sharp(join(input, file))
    .extract({ left: 0, top: 0, width: w, height: cropHeight })
    .resize({ width: 1200, withoutEnlargement: true })
    .webp({ quality: 82 })
    .toFile(join(output, `${name}.webp`))
  console.log(`done: ${name}.webp (${w}x${h} -> ${w}x${cropHeight})`)
}
