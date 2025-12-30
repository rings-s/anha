import { Controller } from "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.js"

export default class extends Controller {
  static targets = [
    "map",
    "lat",
    "lng",
    "detectBtn",
    "detectText",
    "detectSpinner",
    "status",
    "coords",
    "coordsText",
    "address",
    "shareBtn"
  ]

  connect() {
    // Wait for Leaflet to be available
    if (!window.L) {
      setTimeout(() => this.connect(), 100)
      return
    }

    this._initMap()
    // Trigger a resize after a short delay to ensure map renders correctly
    setTimeout(() => {
      this.mapInstance.invalidateSize()
    }, 500)
  }

  disconnect() {
    if (this.mapInstance) {
      this.mapInstance.remove()
    }
  }

  _initMap() {
    // Default to Riyadh, Saudi Arabia if detecting fails
    const defaultLat = 24.7136
    const defaultLng = 46.6753
    const defaultZoom = 12

    // Initialize map with custom options
    this.mapInstance = L.map(this.mapTarget, {
      zoomControl: true,
      scrollWheelZoom: true,
      doubleClickZoom: true,
      touchZoom: true,
    }).setView([defaultLat, defaultLng], defaultZoom)

    // Use a nicer tile layer
    L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap',
    }).addTo(this.mapInstance)

    // Create custom marker icon
    const customIcon = L.divIcon({
      className: 'custom-map-marker',
      html: `<div style="
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #0f6b5f, #ff6b6b);
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 3px solid white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      "></div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 32],
    })

    // Add draggable marker
    this.marker = L.marker([defaultLat, defaultLng], {
      draggable: true,
      icon: customIcon,
      autoPan: true
    }).addTo(this.mapInstance)

    // Update inputs when marker is dragged
    this.marker.on("dragend", () => {
      const latlng = this.marker.getLatLng()
      this._setInputs(latlng.lat, latlng.lng)
      this._reverseGeocode(latlng.lat, latlng.lng)
      this._showStatus("success", "✅ تم تحديث الموقع")
    })

    // Update marker and inputs when map is clicked
    this.mapInstance.on("click", (event) => {
      this.marker.setLatLng(event.latlng)
      this._setInputs(event.latlng.lat, event.latlng.lng)
      this._reverseGeocode(event.latlng.lat, event.latlng.lng)
      this._showStatus("success", "✅ تم تحديد الموقع")
    })

    // Set initial values
    this._setInputs(defaultLat, defaultLng)
  }

  // Public method - can be called from button click
  detectLocation(event) {
    if (event) event.preventDefault()
    this._performDetection()
  }

  // Public method - share location to Google Maps
  shareLocation(event) {
    if (event) event.preventDefault()

    const lat = this.hasLatTarget ? this.latTarget.value : null
    const lng = this.hasLngTarget ? this.lngTarget.value : null

    if (!lat || !lng) {
      this._showStatus("error", "❌ لم يتم تحديد الموقع بعد")
      return
    }

    // Open Google Maps with the coordinates
    const googleMapsUrl = `https://www.google.com/maps?q=${lat},${lng}`
    window.open(googleMapsUrl, '_blank')

    this._showStatus("success", "✅ تم فتح الموقع في Google Maps")
  }

  _performDetection() {
    if (!navigator.geolocation) {
      this._showStatus("error", "❌ المتصفح لا يدعم تحديد الموقع")
      return
    }

    // Show loading state
    this._setLoading(true)
    this._showStatus("info", "🔍 جاري المحاولة...")

    const geoOptions = {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 0
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords

        // Update map and marker
        this.mapInstance.flyTo([latitude, longitude], 16, { duration: 1.5 })
        this.marker.setLatLng([latitude, longitude])
        this._setInputs(latitude, longitude)
        this._reverseGeocode(latitude, longitude)

        const accuracyText = accuracy < 100 ? "دقيقة" : "تقريبية"
        this._showStatus("success", `✅ تم التحديد بنجاح (${accuracyText})`)
        this._setLoading(false)
      },
      (error) => {
        console.error("Geolocation Error:", error)
        let msg = "❌ فشل التحديد: "
        if (error.code === 1) msg += "تم رفض الإذن"
        else if (error.code === 2) msg += "الموقع غير متاح"
        else if (error.code === 3) msg += "انتهت المهلة"
        else msg += "خطأ غير معروف"

        this._showStatus("error", msg)
        this._setLoading(false)

        // If it failed but it's a timeout, try again with lower accuracy
        if (error.code === 3 && geoOptions.enableHighAccuracy) {
          console.log("Retrying with lower accuracy...")
          this._showStatus("info", "🔍 جاري المحاولة بدقة أقل...")
          navigator.geolocation.getCurrentPosition(
            (pos) => {
              const { latitude, longitude } = pos.coords
              this.mapInstance.flyTo([latitude, longitude], 14)
              this.marker.setLatLng([latitude, longitude])
              this._setInputs(latitude, longitude)
              this._reverseGeocode(latitude, longitude)
              this._showStatus("success", "✅ تم التحديد (دقة منخفضة)")
              this._setLoading(false)
            },
            () => {
              this._showStatus("error", "❌ فشل تحديد الموقع تماماً")
              this._setLoading(false)
            },
            { enableHighAccuracy: false, timeout: 10000 }
          )
        }
      },
      geoOptions
    )
  }

  async _reverseGeocode(lat, lng) {
    if (!this.hasAddressTarget) return

    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&addressdetails=1&accept-language=ar`)
      const data = await response.json()

      if (data && data.display_name) {
        const addr = data.address
        const parts = []
        if (addr.suburb) parts.push(addr.suburb)
        if (addr.neighbourhood && addr.neighbourhood !== addr.suburb) parts.push(addr.neighbourhood)
        if (addr.road) parts.push(addr.road)
        if (addr.city || addr.town || addr.village) parts.push(addr.city || addr.town || addr.village)

        const finalAddress = parts.length > 0 ? parts.join(' - ') : data.display_name
        this.addressTarget.value = finalAddress
      }
    } catch (error) {
      console.warn("Reverse Geocoding failed:", error)
    }
  }

  _updateFromMarker() {
    const latlng = this.marker.getLatLng()
    this._setInputs(latlng.lat, latlng.lng)
  }

  _setInputs(lat, lng) {
    const formattedLat = lat.toFixed(6)
    const formattedLng = lng.toFixed(6)

    if (this.hasLatTarget) this.latTarget.value = formattedLat
    if (this.hasLngTarget) this.lngTarget.value = formattedLng

    // Update coordinates display
    if (this.hasCoordsTarget && this.hasCoordsTextTarget) {
      this.coordsTarget.style.display = "block"
      this.coordsTextTarget.textContent = `${formattedLat}, ${formattedLng}`
    }
  }

  _setLoading(isLoading) {
    if (this.hasDetectBtnTarget) {
      this.detectBtnTarget.disabled = isLoading
    }
    if (this.hasDetectTextTarget && this.hasDetectSpinnerTarget) {
      this.detectTextTarget.style.display = isLoading ? "none" : "inline"
      this.detectSpinnerTarget.style.display = isLoading ? "inline" : "none"
    }
  }

  _showStatus(type, message) {
    if (!this.hasStatusTarget) return

    const colors = {
      success: { bg: "rgba(15, 107, 95, 0.1)", border: "1px solid rgba(15, 107, 95, 0.3)", color: "#0f6b5f" },
      error: { bg: "rgba(255, 107, 107, 0.1)", border: "1px solid rgba(255, 107, 107, 0.3)", color: "#dc3545" },
      info: { bg: "rgba(0, 123, 255, 0.1)", border: "1px solid rgba(0, 123, 255, 0.3)", color: "#007bff" }
    }

    const style = colors[type] || colors.info
    this.statusTarget.style.display = "block"
    this.statusTarget.style.background = style.bg
    this.statusTarget.style.border = style.border
    this.statusTarget.style.color = style.color
    this.statusTarget.textContent = message

    // Auto-hide success/info messages after 4 seconds
    if (type !== "error") {
      setTimeout(() => {
        if (this.hasStatusTarget) {
          this.statusTarget.style.display = "none"
        }
      }, 4000)
    }
  }
}
