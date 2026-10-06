/**
 * Dấu ấn Lạc Hồng trên trang chủ.
 *
 * Đây là một chương kể về năng lực thiết kế và chế tác của VinFast, không phải bảng
 * giới thiệu sản phẩm. Ảnh xe đã được chuẩn hoá alpha; bộ xem xoay dùng duy nhất một
 * canvas và chỉ thay đổi góc khi người dùng kéo. Lạc Hồng chưa đi vào luồng đặt lịch.
 */
import { useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { SmartImage } from '../SmartImage'
import { LacHongSpin } from './LacHongSpin'
import { lacHongDisclaimer, lacHongModels, lacHongSpin } from '../../data/lachong'

gsap.registerPlugin(useGSAP, ScrollTrigger)

const statement = 'Năng lực thiết kế và chế tác Việt trong từng chi tiết.'

export function LacHongPassage() {
  const root = useRef(null)
  const [flagship, sedan] = lacHongModels

  useGSAP(
    () => {
      // Ảnh xe KHÔNG còn hoạt cảnh chạy ngang: đã gỡ theo yêu cầu. Đặt hiện sẵn
      // ngay đây để chúng không kẹt ở trạng thái khởi tạo của bản cũ.
      gsap.set('.lachong-figure__car', { opacity: 1, x: 0, xPercent: 0, scale: 1 })

      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      if (reduced) {
        gsap.set('.lachong-word, .lachong-figure__car, .lachong-block__copy > *, .lachong-spin', {
          opacity: 1,
          x: 0,
          y: 0,
          scale: 1,
        })
        return
      }

      /*
       * GHIM MỀM (sticky scroll timeline).
       *
       * Khối tiêu đề đứng yên giữa màn trong khoảng một màn hình cuộn, trong lúc đó
       * từng chữ của câu sáng dần lên. Mục đích là giữ chân người đọc lại vài giây
       * để họ kịp nhận ra VinFast đang có Lạc Hồng, thay vì lướt qua trong nửa giây.
       *
       * KHÔNG khoá bánh xe cuộn. Người dùng cuộn vẫn đi tiếp bình thường, chỉ là
       * quãng đường cuộn đó dùng để chạy hoạt cảnh thay vì đẩy trang. Khoá cứng
       * thao tác cuộn thì trên điện thoại nhiều người tưởng web bị treo.
       *
       * Bỏ ghim ở màn hẹp: ghim trên điện thoại hay giật, và ở đó khối tiêu đề vốn
       * đã chiếm gần hết màn nên không cần giữ thêm.
       */
      const canPin = window.matchMedia('(min-width: 900px)').matches

      gsap.fromTo(
        '.lachong-word',
        { opacity: 0.14 },
        {
          opacity: 1,
          stagger: 0.035,
          ease: 'none',
          scrollTrigger: {
            trigger: '.lachong-passage__heading',
            start: canPin ? 'top 22%' : 'top 78%',
            // Quãng ghim tính theo chiều cao màn hình chứ không đặt cứng: màn thấp
            // mà ghim 760px thì người dùng phải cuộn mãi mới thoát ra được.
            end: canPin ? () => `+=${Math.min(window.innerHeight * 0.85, 720)}` : 'bottom 45%',
            scrub: 0.75,
            pin: canPin,
            pinSpacing: canPin,
            anticipatePin: canPin ? 1 : 0,
            // Xoay ngang máy hay đổi cỡ cửa sổ thì tính lại quãng ghim, nếu không
            // điểm kết thúc giữ nguyên theo chiều cao cũ và hoạt cảnh lệch hẳn.
            invalidateOnRefresh: true,
          },
        },
      )

      gsap.utils.toArray('.lachong-block__copy').forEach((copy) => {
        gsap.fromTo(
          copy.children,
          { y: 30, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.9,
            stagger: 0.075,
            ease: 'power4.out',
            scrollTrigger: { trigger: copy, start: 'top 84%', once: true },
          },
        )
      })

      gsap.fromTo(
        '.lachong-spin',
        { y: 70, scale: 0.94, opacity: 0 },
        {
          y: 0,
          scale: 1,
          opacity: 1,
          duration: 1.25,
          ease: 'power4.out',
          scrollTrigger: { trigger: '.lachong-spin-block', start: 'top 82%', once: true },
        },
      )
    },
    { scope: root },
  )

  const renderMeta = (items) => (
    <dl className="lachong-block__meta">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )

  return (
    <section className="lachong-passage" id="lac-hong" ref={root} aria-labelledby="lachong-title">
      <div className="section-frame">
        <div className="lachong-passage__heading">
          <p className="eyebrow">Dấu ấn VinFast</p>
          <h2 id="lachong-title" aria-label={statement}>
            {statement.split(' ').map((word, index) => (
              <span className="lachong-word" aria-hidden="true" key={`${word}-${index}`}>{word} </span>
            ))}
          </h2>
          <p>
            Lạc Hồng thể hiện khả năng VinFast phát triển một sản phẩm mang yêu cầu riêng
            về thiết kế, vật liệu và không gian ngay tại Việt Nam.
          </p>
        </div>
      </div>

      <div className="section-frame lachong-block lachong-block--flagship">
        <figure className="lachong-figure">
          <SmartImage className="lachong-figure__car" src={flagship.image} alt={`${flagship.name}, dấu ấn chế tác của VinFast`} fit="contain" />
        </figure>
        <div className="lachong-block__copy">
          <span className="lachong-block__narrative">{flagship.narrative}</span>
          <small>{flagship.name}</small>
          <h3>{flagship.headline}</h3>
          <p>{flagship.copy}</p>
          {renderMeta(flagship.meta)}
        </div>
      </div>

      <div className="lachong-spin-chapter">
        <div className="section-frame lachong-spin-block">
          <div className="lachong-spin-block__intro">
            <div>
              <p className="eyebrow">Góc nhìn tương tác</p>
              <h3>Quan sát Lạc Hồng 900 LX từ mọi góc nhìn.</h3>
            </div>
            <p>Giữ và kéo trực tiếp trên xe. Góc nhìn chỉ chuyển động theo tay bạn.</p>
          </div>
          <LacHongSpin frames={lacHongSpin.frames} name={lacHongSpin.name} />
        </div>
      </div>

      <div className="section-frame lachong-block lachong-block--sedan">
        <div className="lachong-block__copy">
          <span className="lachong-block__narrative">{sedan.narrative}</span>
          <small>{sedan.name}</small>
          <h3>{sedan.headline}</h3>
          <p>{sedan.copy}</p>
          {renderMeta(sedan.meta)}
        </div>
        <figure className="lachong-figure">
          <SmartImage className="lachong-figure__car" src={sedan.image} alt={`${sedan.name}, ngôn ngữ thiết kế VinFast`} fit="contain" />
        </figure>
      </div>

      <div className="section-frame">
        <p className="lachong-disclaimer"><span aria-hidden="true">*</span> {lacHongDisclaimer}</p>
      </div>
    </section>
  )
}
