import sharp from "sharp"
import { readdirSync } from "fs"
import { join, extname } from "path"

const files = readdirSync("./images").filter(f => extname(f) === ".png")

for (const file of files) {
  const meta = await sharp(join("./images", file)).metadata()
  console.log(`${file}: ${meta.width}x${meta.height}`)
}
