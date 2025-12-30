import { Controller } from "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.js"

export default class extends Controller {
  connect() {
    document.documentElement.lang = "ar"
    document.documentElement.dir = "rtl"
  }
}
