/* Idea Trellis affiliate-link configuration. Use approved, genuine referral URLs only. */
(()=>{"use strict";
const partners=Object.freeze({
  systeme:{official:"https://systeme.io/",affiliate:null},
  shopify:{official:"https://www.shopify.com/",affiliate:null},
  kit:{official:"https://kit.com/",affiliate:null}
});
document.querySelectorAll("a[data-affiliate]").forEach(link=>{
  const partner=partners[link.getAttribute("data-affiliate")];
  if(!partner)return;
  if(partner.affiliate){
    try{const url=new URL(partner.affiliate);
      if(url.protocol==="https:"){link.href=url.href;link.rel="noopener noreferrer sponsored";link.dataset.referralActive="true";return;}
    }catch(e){}
  }
  link.href=partner.official;link.rel="noopener noreferrer";link.dataset.referralActive="false";
});
})();