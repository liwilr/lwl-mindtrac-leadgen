# Contact filters (data for the Hunter/Apollo request)

Last updated: 2026-10-20

## Contents
1. Settings
2. Word lists

Read by `LeadGen_Tools/contact_spec.py`, which builds one request per company. How the request is used is described in the lead-gen skill (references/enrichment.md); this file holds only the values.
- **Languages:** the `en` column is always used, plus the column(s) of the country profile's `language` (`es`; `en-zh` → `en` + `zh`; `en-si-ta` → `en` + `si` + `ta`, Sri Lanka 2026-10-20: the si/ta words were added at the user's request, not seen at setup). A new language gets a new column at setup.
- **Product-specific inboxes** are in the product profile's `skip_inboxes`.
- **`recruitment_inboxes`** is read by `evidence_to_record.py`: a published email whose local part is one of these words (`hrd@`, `recruitment@`, `proban.hr@`) is never recorded (user, 2026-10-19). Other inboxes a company publishes (`cs@`, `customerservice@`) are kept; `exclude_inboxes` applies only to Hunter/Apollo results.

## Settings
| Key | Value | Meaning |
|---|---|---|
| levels | owner, founder, c_suite, partner, vp, head, director, manager | Apollo management levels for the second search (purchasing staff come from the first search, at any level) |
| hunter_purchasing_department | procurement | Hunter call 1: this department, any seniority |
| hunter_seniority | senior, executive | Hunter call 2 seniority |
| hunter_departments | executive, sales | Hunter call 2 departments (`executive` expresses the leadership levels, `sales` = business development) |
| hunter_limit | 10 | emails per Hunter call (one page) |
| budget | 5 | most non-purchasing people revealed automatically per company |

## Word lists
A title is checked in this order:
1. `exclude_titles` → dropped.
2. `other_departments` → dropped (checked before the wanted lists, so "Chief Financial Officer" is finance, "Post Venta" is after-sales).
3. `business_development` / `procurement` → kept with that department.
4. `leadership` → kept as executive.
5. A title that is only one of the `leadership_bare` words ("Gerente", "Manager") → kept as executive.

Anything else is dropped. Multi-word entries and Chinese match anywhere in the title; single words match whole words only ("intern" is not inside "International").

| List | en | es | pt | zh | id | si | ta |
|---|---|---|---|---|---|---|---|
| business_development | sales, business development, account executive, account manager, key account, salesperson, saleswoman, salesman, commercial | ventas, venta, comercial, vendedor, vendedora, desarrollo de negocios, ejecutivo de cuentas, ejecutiva de cuentas | vendas, comercial, desenvolvimento de negócios | 銷售, 業務, 營業, 業務發展, 業務拓展 | penjualan, sales, pengembangan bisnis | විකුණුම්, ව්‍යාපාර සංවර්ධන | விற்பனை, வணிக மேம்பாடு |
| procurement | procurement, purchasing, purchase, buyer, supply chain, sourcing, import, imports, importing, importer | compras, compra, comprador, compradora, importaciones, importación, importacion, importador, abastecimiento, adquisiciones, cadena de suministro, comex, comercio exterior | compras, comprador, importação, importacao, suprimentos | 採購, 進口, 買手 | pembelian, pengadaan, impor, importir | මිලදී ගැනීම්, ආනයන | கொள்முதல், இறக்குமதி |
| leadership | ceo, chief executive, founder, co-founder, owner, president, managing director, general manager, executive director, partner, proprietor, principal, vp, vice president | gerente general, director general, directora general, dueño, dueña, propietario, propietaria, fundador, fundadora, presidente, presidenta, socio, socia, administrador general | diretor geral, sócio, socio, proprietário, fundador, presidente | 總經理, 董事長, 董事總經理, 創辦人, 東主, 老闆, 總裁, 行政總裁 | direktur utama, presiden direktur, pemilik, pendiri, komisaris, direktur pelaksana, general manager | කළමනාකාර අධ්‍යක්ෂ, සභාපති, හිමිකරු, ආරම්භක | நிர்வாக இயக்குனர், தலைவர், உரிமையாளர், நிறுவனர் |
| leadership_bare | manager, director, owner, administrator | gerente, director, directora, administrador, administradora, propietario, dueño | gerente, diretor | 經理, 主管 | direktur, manajer, kepala, pemilik | කළමනාකරු, අධ්‍යක්ෂ | மேலாளர், இயக்குனர் |
| other_departments | financial, finance, accountant, accounting, cfo, treasury, audit, information technology, information officer, cio, cto, ict, software, developer, systems, after sales, after-sales, aftersales, customer care, service manager, human resource, people & culture, people and culture, legal, counsel, compliance, security, operations, coo, technical director, workshop, logistics, warehouse, mechanical, technician, marketing, brand, communications, advertising | finanzas, financiero, financiera, contador, contadora, contable, contabilidad, tesorería, tesoreria, créditos, creditos, cobranzas, auditor, auditoría, sistemas, informática, informatica, tecnología de la información, postventa, post venta, servicio al cliente, atención al cliente, atencion al cliente, recursos humanos, rrhh, talento humano, gestión humana, gestion humana, abogado, abogada, seguridad, ssoma, soma, operaciones, logística, logistica, almacén, almacen, taller, técnico, tecnico, mecánico, mecanico, procesos, inspector, producción, produccion, mercadeo, publicidad, marca, comunicaciones, nóminas, nominas, presupuesto | financeiro, contabilidade, tecnologia, pós-venda, recursos humanos, jurídico, segurança, operações, logística, marketing | 財務, 會計, 資訊科技, 人力資源, 人事, 法律, 售後, 客戶服務, 物流, 倉庫, 市場推廣, 市場部 | keuangan, akuntansi, akunting, pajak, SDM, sumber daya manusia, personalia, gudang, logistik, bengkel, teknisi, mekanik, pemasaran, hukum, legal, IT, teknologi informasi | ගිණුම්, මූල්‍ය, මානව සම්පත්, අලෙවි | கணக்கு, நிதி, மனித வளம், சந்தைப்படுத்தல் |
| exclude_titles | human resource, recruiter, recruiting, recruitment, talent acquisition, social media, community manager, content creator, content writer, graphic designer, receptionist, office manager, administrative assistant, customer service, customer support, it support, technical support, help desk, helpdesk, hr, intern, trainee, career, careers | recursos humanos, reclutamiento, selección de personal, seleccion de personal, redes sociales, diseñador gráfico, diseñadora gráfica, recepcionista, asistente administrativo, asistente administrativa, servicio al cliente, atención al cliente, atencion al cliente, soporte técnico, soporte tecnico, mesa de ayuda, rrhh, practicante, pasante, soporte, sistemas | suporte técnico, suporte tecnico, suporte, estagiário | 實習, 人力資源, 客戶服務, 前台 | SDM, sumber daya manusia, personalia, rekrutmen, resepsionis, layanan pelanggan, magang, admin media sosial | මානව සම්පත්, පුහුණු | மனித வளம், பயிற்சி |
| exclude_inboxes | career, careers, job, jobs, jobopenings, vacancy, vacancies, hiring, recruit, recruiter, recruiting, recruitment, talent, hr, humanresources, apply, applications, cv, resume, customerservice, support, recycling | rrhh, empleo, empleos, trabajaconnosotros, postulaciones, seleccion, servicioalcliente, servicialcliente, atencionalcliente, soporte, reclamos, reciclaje | recrutamento, vagas, carreiras, curriculo, trabalheconosco, reciclagem | | karir, lowongan, loker, rekrutmen, hrd, cs, layanan |  |  |
| recruitment_inboxes | career, careers, job, jobs, jobopenings, vacancy, vacancies, hiring, recruit, recruiter, recruiting, recruitment, talent, hr, humanresources | rrhh, empleo, empleos, trabajaconnosotros, postulaciones | recrutamento, vagas, carreiras, trabalheconosco | | karir, lowongan, loker, rekrutmen, hrd |  |  |
| purchasing_titles | purchasing, procurement, buyer, import, purchasing manager, import manager | compras, jefe de compras, comprador, importaciones, comercio exterior, comex | compras, importação | 採購 | pembelian, pengadaan, manajer pembelian, impor | මිලදී ගැනීම් | கொள்முதல் |
