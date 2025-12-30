import { Controller } from "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.js"

export default class extends Controller {
    connect() {
        this.buttons = this.element.querySelectorAll('button')

        // Listen for HTMX swaps to handle potential issues, though not strictly needed for class toggle
        document.addEventListener('htmx:afterRequest', (event) => {
            if (this.element.contains(event.detail.elt)) {
                this.updateActiveButton(event.detail.elt)
            }
        })
    }

    updateActiveButton(activeBtn) {
        this.buttons.forEach(btn => {
            btn.classList.remove('active')
        })
        activeBtn.classList.add('active')

        // Trigger a small animation
        if (window.anime) {
            window.anime({
                targets: '#bookings-grid',
                opacity: [0.5, 1],
                translateY: [10, 0],
                easing: 'easeOutExpo',
                duration: 400
            })
        }
    }
}
