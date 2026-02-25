/* =============================================
   app.js — DASTYOR AI Web App JavaScript
   ============================================= */

// ---- PARTICLES ----
(function initParticles() {
    const canvas = document.getElementById('particles');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H, particles = [];

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    function rand(a, b) { return Math.random() * (b - a) + a; }

    class Particle {
        constructor() { this.reset(); }
        reset() {
            this.x = rand(0, W);
            this.y = rand(0, H);
            this.r = rand(0.5, 2.5);
            this.vx = rand(-0.3, 0.3);
            this.vy = rand(-0.3, 0.3);
            this.alpha = rand(0.1, 0.5);
            this.color = Math.random() > 0.6 ? '99,160,255' : '168,85,247';
        }
        update() {
            this.x += this.vx; this.y += this.vy;
            this.alpha += rand(-0.005, 0.005);
            this.alpha = Math.max(0.05, Math.min(0.6, this.alpha));
            if (this.x < 0 || this.x > W || this.y < 0 || this.y > H) this.reset();
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${this.color},${this.alpha})`;
            ctx.fill();
        }
    }

    for (let i = 0; i < 100; i++) particles.push(new Particle());

    function drawLines() {
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(59,130,246,${0.08 * (1 - dist / 120)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }
    }

    function loop() {
        ctx.clearRect(0, 0, W, H);
        particles.forEach(p => { p.update(); p.draw(); });
        drawLines();
        requestAnimationFrame(loop);
    }
    loop();
})();

// ---- NAVBAR SCROLL ----
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
    if (window.scrollY > 40) navbar.classList.add('scrolled');
    else navbar.classList.remove('scrolled');
});

// ---- MOBILE MENU ----
const burger = document.getElementById('burger');
const mobileMenu = document.getElementById('mobileMenu');

burger.addEventListener('click', () => {
    mobileMenu.classList.toggle('open');
});

function closeMobile() {
    mobileMenu.classList.remove('open');
}

// ---- SCROLL ANIMATIONS ----
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.svc-card, .feat-card, .contact-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform += ' translateY(30px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease, border-color 0.4s, box-shadow 0.4s';
    observer.observe(el);
});

// Add visible class styles
const style = document.createElement('style');
style.textContent = `.visible { opacity: 1 !important; transform: translateY(0) !important; }`;
document.head.appendChild(style);

// ---- STAGGERED ANIMATION ----
document.querySelectorAll('.svc-card').forEach((el, i) => {
    el.style.transitionDelay = (i * 0.08) + 's';
});
document.querySelectorAll('.feat-card').forEach((el, i) => {
    el.style.transitionDelay = (i * 0.08) + 's';
});

// ---- SMOOTH SCROLL ----
document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
        const target = document.querySelector(a.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// ---- ACTIVE NAV LINK ----
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-links a');

window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(s => {
        if (window.scrollY >= s.offsetTop - 100) current = s.id;
    });
    navLinks.forEach(a => {
        a.style.color = a.getAttribute('href') === '#' + current ? '#60a5fa' : '';
    });
});
