import { expect, test } from "./fixtures";
import { TEST_SESSION_TOKEN } from "./session";

for (const index of [0, 1, 6]) {
  test(`catalog model ${index} survives navigation and permits another theme`, async ({ page }) => {
    await page.addInitScript((token) => { localStorage.setItem('lang','pt'); localStorage.setItem('storyrus_token',token); }, TEST_SESSION_TOKEN);
    await page.route('**/v1/**', route => {
      const path=new URL(route.request().url()).pathname;
      if(path.endsWith('/auth/me')) return route.fulfill({json:{id:'catalog-test',email:'catalog@example.test',is_guest:false,email_verified:true,terms_accepted_at:'2026-10-30',adult_confirmed_at:'2026-10-30',full_name:'Ana',phone:'11999999999',street:'Rua de Teste',number:'1',city:'São Paulo',postal_code:'01310100',state:'SP',country:'BR',credits:10}});
      if(path.endsWith('/credits')) return route.fulfill({json:{credits:10}});
      return route.fulfill({json:[]});
    });
    await page.goto(`/livro/${index}`);
    const personalize=page.getByTestId('landing-personalize');
    await expect(personalize).toHaveAttribute('href',new RegExp(`modelo=catalog-realistic-${index}`));
    await personalize.click();
    await expect(page).toHaveURL(new RegExp(`/app\\?.*modelo=catalog-realistic-${index}`));
    await expect(page.getByTestId('studio-selected-catalog-model')).toBeVisible();
    await page.getByLabel(/nome do protagonista/i).fill('Lia');
    const title=page.getByLabel(/título do livro/i);
    await expect(title).toHaveAttribute('readonly','');
    if(index===0) await expect(title).toHaveValue('Lia, O Grande Goleiro Do Chile');
    if(index===1) await expect(title).toHaveValue('Lia E Os Primeiros Passos Da Bailarina');
    if(index===6) await expect(title).toHaveValue('O Amor De Mãe');
    const theme=page.getByLabel(/insira o tema desejado/i);
    await theme.fill('Aventura no espaço');
    await expect(theme).toHaveValue('Aventura no espaço');
    await page.screenshot({path:`test-results/catalog-model-${index}.png`,fullPage:true});
  });
}

test('missing cartoon interior cannot silently select a realistic or default model',async({page})=>{
  await page.addInitScript(()=>localStorage.setItem('lang','pt'));
  await page.goto('/livro/12?modo=cartoon');
  await expect(page.getByTestId('catalog-model-unavailable')).toContainText('miolo');
  await expect(page.getByTestId('landing-personalize')).toHaveCount(0);
});
