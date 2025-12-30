import { Application } from "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.js"
import MapController from "/static/js/controllers/map_controller.js"
import LocaleController from "/static/js/controllers/locale_controller.js"
import TabsController from "/static/js/controllers/tabs_controller.js"
import FilterController from "/static/js/controllers/filter_controller.js"
import MobileMenuController from "/static/js/controllers/mobile_menu_controller.js"
import RedirectController from "/static/js/controllers/redirect_controller.js"

const application = Application.start()
application.register("map", MapController)
application.register("locale", LocaleController)
application.register("tabs", TabsController)
application.register("filter", FilterController)
application.register("mobile-menu", MobileMenuController)
application.register("redirect", RedirectController)
