import { l } from './i18n.js';
import { icon } from './icons.js';

// User-provided illustrations, not photographs of the customer's property.
// Match declared installation type only; never infer it from a name or capacity.
export const plantIllustrations = {
  RESIDENTIAL: {file:'plant_residential.jpg', label:()=>l('Nhà ở','Residential')},
  ROOFTOP_CI: {file:'plant_commercial.jpg', label:()=>l('Mái nhà xưởng / thương mại','Commercial rooftop')},
  GROUND_MOUNT: {file:'plant_utility.jpg', label:()=>l('Trang trại điện mặt trời','Ground-mounted solar')},
};

export function plantMedia(ui, site, compact = false) {
  const kind = String(site.declared_specs?.plant_type || site.plant_type || '').toUpperCase();
  const asset = plantIllustrations[kind];
  if (!asset) return ui.div(compact ? 'site-emblem' : 'plant-media-placeholder', icon('plant'),
    compact ? null : ui.e('span',l('Chưa có ảnh công trình','No plant photograph')));
  const figure = ui.e('figure','',compact ? 'plant-media compact' : 'plant-media');
  const img = ui.e('img');
  img.src = '/static/img/' + asset.file;
  img.alt = asset.label() + ' · ' + l('ảnh minh họa','illustration');
  img.loading = 'lazy'; img.width = 1376; img.height = 768;
  figure.append(img,ui.e('figcaption',l('Ảnh minh họa','Illustration')));
  return figure;
}
