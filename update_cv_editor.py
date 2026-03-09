import re

file_path = 'c:\\Users\\User\\hujjatchi_ai_bot\\webapp\\cv.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace the Personal Info to Tools HTML section
html_section_start = '<!-- PERSONAL INFO -->'
html_section_end = '<!-- PREVIEW PANE -->'

new_html = """<!-- PERSONAL INFO -->
      <div class="editor-section">
        <div class="section-label" data-i18n="cv_section_personal">Shaxsiy ma'lumotlar</div>
        
        <!-- Profile Image -->
        <div class="photo-upload-area" onclick="document.getElementById('imgInput').click()">
            <div id="photoPrev" class="photo-preview-box">
                <span class="text-2xl opacity-50">📷</span>
            </div>
            <input type="file" id="imgInput" accept="image/*" class="hidden" onchange="handleImage(this)">
            <span class="upload-btn-label" data-i18n="cv_upload_img">Rasm yuklash</span>
            <span class="upload-sub" data-i18n="cv_rec_img">Professional tasvir tavsiya etiladi</span>
        </div>

        <div class="field-group">
            <label class="field-label" data-i18n="cv_name_label">Ism Familiya</label>
            <input type="text" id="f_name" class="field-input bold" placeholder="Alisherov M." data-i18n="ph_cv_name" data-i18n-attr="placeholder" oninput="updateCV()">
        </div>

        <div class="field-group">
            <label class="field-label" data-i18n="cv_role_label">Kasb</label>
            <input type="text" id="f_role" class="field-input" placeholder="Senior UI/UX Designer" data-i18n="ph_cv_role" data-i18n-attr="placeholder" oninput="updateCV()">
        </div>

        <div class="two-col">
            <div class="field-group">
                <label class="field-label" data-i18n="cv_phone_label">Telefon</label>
                <input type="text" id="f_phone" class="field-input" placeholder="+998 90 123 45 67" data-i18n="ph_cv_phone" data-i18n-attr="placeholder" oninput="updateCV()">
            </div>
            <div class="field-group">
                <label class="field-label" data-i18n="cv_email_label">Email</label>
                <input type="email" id="f_email" class="field-input" placeholder="email@example.com" data-i18n="ph_email" data-i18n-attr="placeholder" oninput="updateCV()">
            </div>
        </div>

        <div class="field-group">
            <label class="field-label" data-i18n="cv_loc_label">Manzil</label>
            <input type="text" id="f_loc" class="field-input" placeholder="Toshkent Shahri" data-i18n="ph_cv_loc" data-i18n-attr="placeholder" oninput="updateCV()">
        </div>

        <div class="field-group">
            <label class="field-label" data-i18n="cv_about_label">Qisqa professional yutuqlar xulosasi</label>
            <textarea id="f_about" class="field-input" style="height: 100px; resize: none;" placeholder="5+ yillik tajribaga ega dasturchi, loyiha tezligini 30% ga oshirgan..." data-i18n="ph_cv_about" data-i18n-attr="placeholder" oninput="updateCV()"></textarea>
        </div>
      </div>

      <div class="editor-divider"></div>

      <!-- EXPERIENCE -->
      <div class="editor-section">
        <div class="section-label" data-i18n="cv_experience">Ish Tajribasi</div>
        <div id="expList" style="margin-bottom:10px;"></div>
        <button onclick="addExp()" class="add-btn" data-i18n="cv_add_exp">+ Tajriba qo'shish</button>
      </div>

      <div class="editor-divider"></div>

      <!-- ACHIEVEMENTS -->
      <div class="editor-section">
        <div class="section-label" data-i18n="cv_achievements">Asosiy Yutuqlar</div>
        <div id="achList" style="margin-bottom:10px;"></div>
        <button onclick="addAch()" class="add-btn" data-i18n="cv_add_ach">+ Yutuq qo'shish</button>
      </div>

      <div class="editor-divider"></div>

      <!-- EDUCATION -->
      <div class="editor-section">
        <div class="section-label" data-i18n="cv_education">Ta'lim</div>
        <div id="eduList" style="margin-bottom:10px;"></div>
        <button onclick="addEdu()" class="add-btn" data-i18n="cv_add_edu">+ Ta'lim qo'shish</button>
      </div>

      <div class="editor-divider"></div>

      <!-- SKILLS -->
      <div class="editor-section">
        <div class="section-label" data-i18n="cv_skills">Asosiy Ko'nikmalar</div>
        <div class="field-group">
          <input type="text" id="skillInput" class="field-input" placeholder="Liderlik xislatlari..." data-i18n="ph_skill" data-i18n-attr="placeholder" onkeydown="handleSkillAdd(event)">
          <div id="skillsWrap" class="flex flex-wrap gap-2 mt-3"></div>
        </div>
      </div>

      <div class="editor-divider"></div>

      <!-- TOOLS -->
      <div class="editor-section">
        <div class="section-label" data-i18n="cv_tools">Dasturlar va Texnologiyalar</div>
        <div class="field-group">
          <input type="text" id="toolInput" class="field-input" placeholder="Dastur nomini yozib ENTER bosing (Masalan: Figma)..." onkeydown="handleToolAdd(event)">
          <div id="toolsWrap" class="flex flex-wrap gap-2 mt-3"></div>
        </div>
      </div>

      <div class="editor-bottom"></div>
    </div>

    """

content = content.split(html_section_start)[0] + new_html + html_section_end + content.split(html_section_end)[1]

# 2. Update the JS render functions
js_update = """
    // Expanders (Exp/Edu)
    function renderExp() {
      document.getElementById('expList').innerHTML = experiences.map((ex, i) => `
                <div class="repeater-card group">
                    <button class="remove-btn opacity-0 group-hover:opacity-100" onclick="removeExp(${ex.id})">×</button>
                    <input type="text" class="repeater-input" style="font-weight:bold;" placeholder="Lavozim" value="${ex.title}" oninput="experiences[${i}].title=this.value; updateCV()">
                    <div class="two-col mb-1">
                        <div class="field-group" style="margin-bottom:0;"><input type="text" class="repeater-input" placeholder="Kompaniya" value="${ex.company}" oninput="experiences[${i}].company=this.value; updateCV()"></div>
                        <div class="field-group" style="margin-bottom:0;"><input type="text" class="repeater-input" placeholder="Yillar" value="${ex.date}" oninput="experiences[${i}].date=this.value; updateCV()"></div>
                    </div>
                    <textarea class="repeater-textarea" style="height: 60px;" placeholder="Kuchli fe'l + vazifa + o'lchanadigan natija (Masalan: Savdoni 20% ga oshirdim...)" oninput="experiences[${i}].desc=this.value; updateCV()">${ex.desc}</textarea>
                </div>
            `).join('');
      if (window.SmartAutoFill) SmartAutoFill.initDynamic();
    }
    function addExp() { experiences.push({ id: Date.now(), title: '', company: '', date: '', desc: '' }); renderExp(); updateCV(); }
    function removeExp(id) { experiences = experiences.filter(x => x.id !== id); renderExp(); updateCV(); }

    function renderAch() {
      document.getElementById('achList').innerHTML = achievements.map((a, i) => `
                <div class="repeater-card group">
                    <button class="remove-btn opacity-0 group-hover:opacity-100" onclick="removeAch(${a.id})">×</button>
                    <textarea class="repeater-textarea" style="height: 50px;" placeholder="Erishilgan yirik yutuq (Masalan: Yilning eng yaxshi xodimi 2023)..." oninput="achievements[${i}].desc=this.value; updateCV()">${a.desc}</textarea>
                </div>
            `).join('');
    }
    function addAch() { achievements.push({ id: Date.now(), desc: '' }); renderAch(); updateCV(); }
    function removeAch(id) { achievements = achievements.filter(x => x.id !== id); renderAch(); updateCV(); }

    function renderEdu() {
      document.getElementById('eduList').innerHTML = education.map((ed, i) => `
                <div class="repeater-card group">
                    <button class="remove-btn opacity-0 group-hover:opacity-100" onclick="removeEdu(${ed.id})">×</button>
                    <input type="text" class="repeater-input" style="font-weight:bold;" placeholder="Daraja yoki Kurs" value="${ed.title}" oninput="education[${i}].title=this.value; updateCV()">
                    <div class="two-col mb-1">
                        <div class="field-group" style="margin-bottom:0;"><input type="text" class="repeater-input" placeholder="Oliygoh" value="${ed.company}" oninput="education[${i}].company=this.value; updateCV()"></div>
                        <div class="field-group" style="margin-bottom:0;"><input type="text" class="repeater-input" placeholder="Yillar" value="${ed.date}" oninput="education[${i}].date=this.value; updateCV()"></div>
                    </div>
                    <textarea class="repeater-textarea" style="height: 50px;" placeholder="Qo'shimcha ma'lumotlar..." oninput="education[${i}].desc=this.value; updateCV()">${ed.desc}</textarea>
                </div>
            `).join('');
      if (window.SmartAutoFill) SmartAutoFill.initDynamic();
    }
"""

content = re.sub(r'// Expanders \(Exp/Edu\).*?function removeEdu\(id\) {.*?}', js_update.strip(), content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")
