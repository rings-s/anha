import { Controller } from "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.js"

export default class extends Controller {
    static targets = ["tab", "panel"]
    static classes = ["active"]

    connect() {
        this.activeTabIndex = 0
        this.showTab(this.activeTabIndex)
    }

    switch(event) {
        const index = this.tabTargets.indexOf(event.currentTarget)
        this.showTab(index)
    }

    showTab(index) {
        this.tabTargets.forEach((tab, i) => {
            tab.classList.toggle(this.activeClass, i === index)
        })

        this.panelTargets.forEach((panel, i) => {
            panel.classList.toggle("hidden", i !== index)
            if (i === index) {
                panel.classList.add("animate-in")
                // Trigger anime.js if available
                if (window.anime) {
                    window.anime({
                        targets: panel,
                        opacity: [0, 1],
                        translateY: [10, 0],
                        easing: 'easeOutExpo',
                        duration: 600
                    })
                }
            }
        })
    }
}
