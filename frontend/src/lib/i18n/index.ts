import { register, init, getLocaleFromNavigator } from 'svelte-i18n';

register('en', () => import('./en.json'));
register('de', () => import('./de.json'));

const supported = ['en', 'de'];
const navigatorLocale = getLocaleFromNavigator() ?? 'en';
const initialLocale = supported.find((l) => navigatorLocale.startsWith(l)) ?? 'en';

init({
	fallbackLocale: 'en',
	initialLocale
});
