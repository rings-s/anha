import { Controller } from "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.js"

export default class extends Controller {
    static values = {
        url: String,
        delay: Number,
    }

    connect() {
        const url = this.urlValue
        const delay = Number.isFinite(this.delayValue) ? this.delayValue : 0
        if (!url) {
            return
        }
        this.timeoutId = setTimeout(() => {
            window.location.assign(url)
        }, Math.max(0, delay))
    }

    disconnect() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId)
        }
    }
}
