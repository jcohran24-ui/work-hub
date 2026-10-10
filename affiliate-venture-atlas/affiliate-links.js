/* Idea Trellis affiliate-link configuration. Use approved, genuine referral URLs only. */
(()=>{"use strict";
const partners=Object.freeze({
  systeme:{official:"https://systeme.io/",affiliate:"https://systeme.io/tr/2/161/15056344105/39837047/447807792e1392d2a8c0533efc41603aadbd41b00"},
  shopify:{official:"https://www.shopify.com/",affiliate:null},
  kit:{official:"https://kit.com/",affiliate:null}
});
document.querySelectorAll("a[data-affiliate]").forEach(link=>{
  const partner=partners[link.getAttribute("data-affiliate")];
  if(!partner)return;
  if(partner.affiliate){
    try{const url=new URL(partner.affiliate);
      if(url.protocol==="https:"){link.href=url.href;link.rel="noopener noreferrer sponsored";link.dataset.referralActive="true";const notice=document.createElement("span");notice.textContent=" (affiliate link — we may earn a commission)";notice.style.fontSize=".76em";notice.style.color="#526b5b";link.insertAdjacentElement("afterend",notice);return;}
    }catch(e){}
  }
  link.href=partner.official;link.rel="noopener noreferrer";link.dataset.referralActive="false";
});
})();