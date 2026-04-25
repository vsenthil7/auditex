p = r"C:/Users/v_sen/Documents/Projects/0001_Hack0014_Vertex_Swarm_Tashi/auditex/frontend/tests/demo/end-to-end-demo.spec.ts"
t = open(p, 'r', encoding='utf-8').read()
old = """OLD_BLOCK
      // 7) Show the result: scroll through the detail panel slowly so viewers see the
      // executor verdict, reviewer panel, vertex hash, compliance report.
      for (let y = 0; y <= 1500; y += 200) {
        await detail.evaluate((el, pos) => el.scrollTo({ top: pos, behavior: 'smooth' }), y)
        await page.waitForTimeout(900)
      }

      // Pause 2s on the completed result so viewers see the final state
      await page.waitForTimeout(2000)
"""
old = old.split("OLD_BLOCK", 1)[1].lstrip().rstrip()
new = """NEW_BLOCK
      // 7a) Wait for executor block to populate inside the detail panel.
      // The list shows COMPLETED ~3s before /tasks/{id} returns full executor + review + vertex.
      await expect(detail.locator('text=/Step 2/i').first()).toBeVisible({ timeout: 30000 })
      await page.waitForTimeout(1500)

      // 7b) Expand each of the 5 pipeline step accordions: Submit / Execute / Review / Vertex / Report.
      const steps = detail.locator('button', { hasText: /^Step [1-5]/ })
      const stepCount = await steps.count()
      for (let s = 0; s < Math.min(stepCount, 5); s++) {
        await steps.nth(s).scrollIntoViewIfNeeded()
        await page.waitForTimeout(400)
        await steps.nth(s).click()
        await page.waitForTimeout(900)
      }

      // 7c) Slow scroll through expanded panel: executor verdict, reviewers, vertex hash, report.
      for (let y = 0; y <= 2000; y += 250) {
        await detail.evaluate((el, pos) => el.scrollTo({ top: pos, behavior: 'smooth' }), y)
        await page.waitForTimeout(1100)
      }

      // 7d) Linger on the final state so viewer absorbs the full result.
      await page.waitForTimeout(3000)
"""
new = new.split("NEW_BLOCK", 1)[1].lstrip().rstrip()
n = t.count(old)
t = t.replace(old, new)
open(p, 'w', encoding='utf-8').write(t)
print('patched count:', n)
