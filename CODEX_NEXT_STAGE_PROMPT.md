# Ready-to-paste prompt for Codex

Перед началом добавь в репозиторий два переданных документа по указанным в них
путям:

- `docs/canon/WORLD_ZERO_DIVINE_ONTOLOGY_CANON_V0_1.md`
- `docs/pilot/WORLD_ZERO_PILOT_0_1_DIRECTION.md`

Затем передай Codex следующий запрос.

---

Переключись в **Plan mode**. Сейчас требуется только read-only аудит и новый
план. Ничего не редактируй, не коммить, не запускай сетевые сервисы и не начинай
реализацию.

Сначала прочитай полностью и в указанном порядке:

1. `AGENTS.md`;
2. `WORLD_ZERO_CURRENT_STATE.md`;
3. актуальное начало `README.md`;
4. `docs/CANON_SOURCE_ORDER.md`;
5. `docs/canon/WORLD_ZERO_DIVINE_ONTOLOGY_CANON_V0_1.md`;
6. `docs/pilot/WORLD_ZERO_PILOT_0_1_DIRECTION.md`;
7. релевантные current specs и acceptance records D.1.4.2 и D.2.0–D.2.3;
8. реализацию и тесты `DivineRuntime`, `DivineAgent`, `DivineMindState`,
   `DivineActionGateway`, `Presence`, Herald/subjective evidence,
   `PersistentProject`, `ProjectRuntime`, `SubjectiveWorldView`, Hydrology,
   PhysicalAffordanceBridge и Aqueous Echo;
9. существующий план `World Zero Pilot 0.1 — The Silver Thread`, если он
   сохранён в рабочем контексте или репозитории.

Применяй `docs/CANON_SOURCE_ORDER.md`, но считай два новых документа последним
явным решением пользователя для божественной онтологии и направления Pilot
0.1. Они не меняют автоматически статус executable checkpoints.

Проверь реальный Git status, tag и локальные документы. Ожидаемый baseline —
D.2.3 user-local accepted/frozen с результатами 139 tests, 10/10, 19/19, 26/26,
26/26. Если локальный репозиторий говорит иначе, только сообщи расхождение и
его источник; ничего не повышай и не понижай по статусу.

Старый Nereid-centred план не реализовывай без переработки. В частности, новый
план обязан учитывать:

- Pilot 0.1 — это `Ash Valley`, а не только `The Silver Thread`;
- три независимые нити: Silver/Nature/Nereid, Death/cult/necromancy и
  Trade/contracts;
- активных Богов, а не только Нереиду, Trade House и культ;
- Нереида не должна быть load-bearing центром пилота;
- удаление Нереиды не должно останавливать Death и Trade histories;
- Арра не получает `water_sense` по умолчанию;
- terminal допустим как внутренний harness, но внешний Player View должен быть
  минимально визуальным;
- никакого Story Director, автоматических quest triggers и player-assigned
  Projects;
- никаких новых копий Ledger, clock, evidence store или physical truth;
- Боги получают только доставленные субъективные сведения, но обладают гораздо
  более сильной памятью и cognition, чем люди;
- знание не является универсальным разрешением на divine action: допускаются
  identity/place/trace/condition selectors, однако объективное разрешение не
  возвращает Богу answer key;
- обычные physical locality checks не ослабляются ради Богов — предложи
  отдельный additive divine/metaphysical resolver seam;
- каждый executable increment должен завершаться player-visible loop;
- frozen LAW и counterfactuals нельзя ослаблять.

Подготовь единый конкретный план со следующими разделами:

1. **Read-only audit verdict:** checkpoint, Git state, конфликты документов и
   техническая готовность.
2. **Product boundary:** что именно увидит и сможет сделать игрок за первые
   30–45 минут.
3. **Actor and thread map:** чего каждый субъект хочет до игрока, что знает,
   чего не знает и какими способами может действовать.
4. **Reuse / integration / missing matrix:** что уже есть, что не соединено и
   чего действительно нет.
5. **Smallest additive architecture:** точный D.1→D.2 seam для первого
   полноценного Бога, без дублирования истины, времени и evidence ownership.
6. **Divine ontology representation:** минимальные типы/контракты, нужные
   пилоту; не пытайся реализовать всю метафизику сразу.
7. **Vertical increments:** зависимости, затрагиваемые файлы, player-visible
   результат, acceptance stop и что вырезать первым для каждого этапа.
8. **Acceptance design:** offline LAW, negative leakage checks,
   no-player/no-Nereid counterfactuals, neural SIGNAL gates и human playtest
   criteria.
9. **Visual surface:** 2–3 реалистичных варианта минимального Player View,
   рекомендация с оценкой стоимости и отдельный Creator/Investor View.
10. **Risk and estimate:** относительные S/M/L оценки, критический путь,
    технические риски и scope cuts, которые не уничтожают product thesis.
11. **Documentation migration:** какие файлы нужно будет добавить или изменить
    после утверждения плана, включая `CANON_SOURCE_ORDER`, current state, spec и
    acceptance contract.

Не подменяй неизвестные решения уверенными утверждениями. Раздел о divine
conflict/death из нового канона имеет статус provisional и требует расширения;
не кодируй его в Pilot 0.1 без отдельного решения.

В конце дай ясный GO/REVISE/NO-GO verdict для предложенного масштаба. Не
реализуй план до моего явного подтверждения.

---

После ответа Codex не нажимай **Implement plan** сразу. Сначала проверь план на
соответствие двум новым документам и принеси его на содержательный разбор.
