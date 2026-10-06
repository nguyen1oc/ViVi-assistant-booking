/**
 * Nội dung chương Lạc Hồng trên trang chủ.
 *
 * COPY CONTRACT: ưu tiên kể về năng lực và bản sắc VinFast; không biến khối này thành
 * bảng thông số hoặc CTA bán xe. Lạc Hồng chưa nằm trong catalogue và không dẫn vào booking.
 * MEDIA CONTRACT: ảnh hero/emerge phải là PNG/WebP alpha thật, không ghép nền studio.
 */
import { showcaseImage } from '../media/assets'
import { showcaseMediaMap } from '../media/vehicle-media-map'

const spinFrames = showcaseMediaMap['lac-hong-900lx'].spin.map((path) => showcaseImage(path))

export const lacHongSpin = {
  id: 'lac-hong-900lx',
  name: 'Lạc Hồng 900 LX',
  frames: spinFrames,
}

export const lacHongModels = [
  {
    id: 'lac-hong-900lx',
    name: 'Lạc Hồng 900 LX',
    ordinal: 'LX',
    body: 'SUV nguyên thủ',
    image: showcaseImage('lac-hong-900lx/hero-v2.png'),
    narrative: 'Phát triển tại Việt Nam',
    headline: 'Một mẫu xe mang dấu ấn Việt từ thiết kế đến hoàn thiện.',
    copy: 'Lạc Hồng 900 LX cho thấy khả năng VinFast phát triển sản phẩm theo những yêu cầu riêng về tỷ lệ, vật liệu và không gian. Đây là mẫu xe thể hiện năng lực thương hiệu, không phải sản phẩm đang mở bán.',
    meta: [
      { label: 'Ngôn ngữ', value: 'Bản sắc Việt' },
      { label: 'Vai trò', value: 'Dấu ấn VinFast' },
    ],
  },
  {
    id: 'lac-hong-900s',
    name: 'Lạc Hồng 900S',
    ordinal: '900S',
    body: 'Sedan hạng sang',
    image: showcaseImage('lac-hong-900s/hero-v2.png'),
    narrative: 'Cùng một dấu ấn thiết kế',
    headline: 'Một tinh thần thiết kế trên hai kiểu dáng khác nhau.',
    copy: 'Từ dáng SUV bề thế đến thân xe sedan liền mạch, các chi tiết nhận diện vẫn được duy trì nhất quán. Hai kiểu dáng cho thấy cách VinFast phát triển cùng một tinh thần thiết kế trên nhiều dòng sản phẩm.',
    meta: [
      { label: 'Phạm vi', value: 'Từ SUV đến sedan' },
      { label: 'Tinh thần', value: 'Chế tác tại Việt Nam' },
    ],
  },
]

/** Ảnh xe lớn ở đầu trang chủ. */
export const lacHongHero = {
  src: showcaseImage('lac-hong-900lx/hero-v2.png'),
  alt: 'Lạc Hồng 900 LX, ảnh studio nền trong suốt',
  name: 'Lạc Hồng 900 LX',
}

/** Ảnh đầu xe dùng cho khối "xe tiến ra từ chiều sâu". Ảnh gốc 768 px nên chỉ dùng ở cỡ vừa. */
export const lacHongEmerge = {
  src: showcaseImage('lac-hong-900lx/front-emerge-v2.png'),
  alt: 'Lạc Hồng nhìn chính diện trên nền trong suốt',
}

/** Ảnh tư liệu thật dùng rất nhỏ trong typography của cảnh "Đường nét Việt". */
export const lacHongContext = {
  src: showcaseImage('lac-hong-900lx/origin-vietnam.jpg'),
  alt: 'Lạc Hồng 900 LX tại không gian trưng bày trước quốc kỳ Việt Nam',
}

export const lacHongDisclaimer =
  'Hình ảnh thuộc phiên bản tiền thương mại, chỉ mang tính minh hoạ và có thể thay đổi trong quá trình phát triển.'
