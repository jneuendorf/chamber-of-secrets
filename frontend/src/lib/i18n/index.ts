import { register, init, getLocaleFromNavigator } from "svelte-i18n";

register("en", () => import("./en.json"));
register("de", () => import("./de.json"));

const supported = ["en", "de"];
const navigatorLocale = getLocaleFromNavigator() ?? "de";
const initialLocale = supported.find((l) => navigatorLocale.startsWith(l)) ?? "de";

init({
    fallbackLocale: "de",
    initialLocale,
});
