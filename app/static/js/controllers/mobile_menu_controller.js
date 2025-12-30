import { Controller } from "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.js"

export default class extends Controller {
    static targets = ["menu", "iconOpen", "iconClose"]

    connect() {
        console.log("Mobile Menu Controller Connected")
        // Ensure initial state matches HTML (hidden)
        if (!this.menuTarget.classList.contains("hidden")) {
            this.close()
        }
    }

    toggle(event) {
        if (event) event.preventDefault()
        console.log("Toggle mobile menu")

        if (this.menuTarget.classList.contains("hidden")) {
            this.open()
        } else {
            this.close()
        }
    }

    open() {
        // 1. Remove hidden to make it displayable
        this.menuTarget.classList.remove("hidden")

        // 2. Use requestAnimationFrame to trigger transition *after* display block is applied
        requestAnimationFrame(() => {
            this.menuTarget.classList.remove("opacity-0", "translate-y-[-10px]")
            this.menuTarget.classList.add("opacity-100", "translate-y-0")
        })

        // 3. Swap Icons
        this.iconOpenTarget.classList.add("hidden")
        this.iconCloseTarget.classList.remove("hidden")
    }

    close() {
        // 1. Start transition out
        this.menuTarget.classList.add("opacity-0", "translate-y-[-10px]")
        this.menuTarget.classList.remove("opacity-100", "translate-y-0")

        // 2. Swap Icons immediately
        this.iconOpenTarget.classList.remove("hidden")
        this.iconCloseTarget.classList.add("hidden")

        // 3. Wait for transition, then hide element
        // Clear any existing timeout to prevent race conditions
        if (this.timeout) clearTimeout(this.timeout)

        this.timeout = setTimeout(() => {
            // Double check we are still closed (user didn't reopen quickly)
            if (this.menuTarget.classList.contains("opacity-0")) {
                this.menuTarget.classList.add("hidden")
            }
        }, 300) // Match duration-300
    }
}
