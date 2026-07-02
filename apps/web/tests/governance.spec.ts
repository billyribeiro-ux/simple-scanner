import { expect, type Page, test } from '@playwright/test';

const cycle = {
  research_cycle_id: 'cycle-001',
  cycle_date: '2026-07-01',
  cycle_type: 'daily',
  status: 'created',
  symbols: ['AAPL', 'SPY'],
  intervals: ['1min'],
  start: '2026-06-01T13:30:00Z',
  end: '2026-06-30T20:00:00Z',
  session: 'rth',
  active_model_version: 'champion-v1',
  challenger_model_version: 'challenger-v2',
  proposal_ids: ['proposal-001'],
  comparison_ids: ['comparison-001'],
  stale_window_status: { status: 'clean', dirty_window_count: 0 },
  summary: { model_activation_unchanged: true },
  warnings: [],
  config_hash: 'hash-cycle-001',
  input_fingerprint: 'fingerprint-cycle-001',
  created_at: '2026-07-01T12:00:00Z',
};

const baseProposal = {
  proposal_id: 'proposal-001',
  research_cycle_id: 'cycle-001',
  proposal_type: 'champion_challenger',
  status: 'PROPOSED',
  champion_model_version: 'champion-v1',
  challenger_model_version: 'challenger-v2',
  recommended_action: 'APPROVE_CHALLENGER_FOR_ACTIVATION',
  readiness_status: 'PASS',
  evidence_summary: { sample_count: 25 },
  champion_metrics: { average_r: 0.1 },
  challenger_metrics: { average_r: 0.2 },
  delta_metrics: { average_r: 0.1 },
  pass_fail_gates: { validation_pass: true, all_passed: true },
  rejection_reasons: [],
  approval_required: true,
  comparison_ids: ['comparison-001'],
  validation_report_ids: ['validation-001'],
  calibration_audit_ids: ['calibration-001'],
  drift_report_ids: ['drift-001'],
  model_review_report_ids: ['review-001'],
  created_at: '2026-07-01T12:10:00Z',
  updated_at: '2026-07-01T12:10:00Z',
};

const baseSchedulerJob = {
  job_id: 'scheduler-001',
  job_type: 'data_quality_report',
  status: 'QUEUED',
  priority: 100,
  scheduled_for: null,
  started_at: null,
  completed_at: null,
  failed_reason: null,
  payload: { symbols: ['AAPL', 'SPY'], intervals: ['1min'] },
  result: {},
  warnings: [],
  research_cycle_id: null,
  created_by: 'operator-ui',
  created_at: '2026-07-01T12:40:00Z',
  updated_at: '2026-07-01T12:40:00Z',
};

function schedulerSummary(jobs: Array<Record<string, unknown>>) {
  const latestJob = jobs[0] ?? null;
  const failed = jobs.find((job) => ['FAILED', 'BLOCKED'].includes(String(job.status))) ?? null;
  return {
    status: 'ok',
    queued_jobs: jobs.filter((job) => job.status === 'QUEUED').length,
    running_jobs: jobs.filter((job) => job.status === 'RUNNING').length,
    failed_jobs: jobs.filter((job) => ['FAILED', 'BLOCKED'].includes(String(job.status))).length,
    completed_jobs: jobs.filter((job) => job.status === 'COMPLETED').length,
    cancelled_jobs: jobs.filter((job) => job.status === 'CANCELLED').length,
    latest_job: latestJob,
    latest_failed_job: failed,
    latest_events: [
      {
        event_id: 'scheduler-event-001',
        job_id: 'scheduler-001',
        event_type: 'JOB_CREATED',
        message: 'Scheduler job queued.',
        metadata: {},
        created_at: '2026-07-01T12:40:00Z',
      },
    ],
    persistence_backend: 'sqlite',
    warnings: ['Scheduler is bounded and does not activate models.'],
  };
}

function json(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    headers: {
      'access-control-allow-headers': 'content-type',
      'access-control-allow-methods': 'GET,POST,OPTIONS',
      'access-control-allow-origin': '*',
    },
    body: JSON.stringify(body),
  };
}

function corsPreflight() {
  return {
    status: 204,
    headers: {
      'access-control-allow-headers': 'content-type',
      'access-control-allow-methods': 'GET,POST,OPTIONS',
      'access-control-allow-origin': '*',
    },
  };
}

async function installGovernanceMocks(page: Page) {
  let proposal: Record<string, unknown> = { ...baseProposal };
  let schedulerJobs: Array<Record<string, unknown>> = [{ ...baseSchedulerJob }];
  const schedulerEvents: Array<Record<string, unknown>> = [
    {
      event_id: 'scheduler-event-001',
      job_id: 'scheduler-001',
      event_type: 'JOB_CREATED',
      message: 'Scheduler job queued.',
      metadata: {},
      created_at: '2026-07-01T12:40:00Z',
    },
  ];
  const calls: {
    activate: number;
    approve: number;
    dryRun: number;
    schedulerCreate: number;
    runPending: number;
    cycleCreateBody: unknown;
    schedulerCreateBody: unknown;
    activateBody: unknown;
    requests: string[];
  } = {
    activate: 0,
    approve: 0,
    dryRun: 0,
    schedulerCreate: 0,
    runPending: 0,
    cycleCreateBody: null,
    schedulerCreateBody: null,
    activateBody: null,
    requests: [],
  };

  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.port !== '8000') {
      await route.continue();
      return;
    }
    calls.requests.push(`${request.method()} ${url.pathname}`);
    if (request.method() === 'OPTIONS') {
      await route.fulfill(corsPreflight());
      return;
    }

    if (url.pathname === '/health') {
      await route.fulfill(
        json({
          status: 'ok',
          time: '2026-07-01T12:00:00Z',
          persistence: { backend: 'sqlite', database_reachable: true },
        }),
      );
      return;
    }
    if (url.pathname === '/config') {
      await route.fulfill(
        json({
          app_name: 'Adaptive Market Decoder',
          default_symbols: [
            'AMZN',
            'AAPL',
            'TSLA',
            'SPY',
            'QQQ',
            'IWM',
            'NVDA',
            'GOOGL',
            'BABA',
            'SHOP',
          ],
          timezone: 'America/New_York',
          min_confidence: 0.7,
          fmp_api_key_configured: false,
        }),
      );
      return;
    }
    if (url.pathname === '/operations/research-status') {
      await route.fulfill(
        json({
          status: 'ok',
          latest_research_cycle: cycle,
          latest_model_proposal: proposal,
          latest_scheduler_job: schedulerJobs[0],
          queued_scheduler_jobs: schedulerJobs.filter((job) => job.status === 'QUEUED').length,
          failed_scheduler_jobs: schedulerJobs.filter((job) =>
            ['FAILED', 'BLOCKED'].includes(String(job.status)),
          ).length,
          active_model_version: 'champion-v1',
          active_model_review_status: 'PASS',
          latest_calibration_drift_severity: 'INFO',
          stale_windows_summary: { status: 'clean', dirty_window_count: 0 },
          data_quality_summary: { status: 'ok', invalid_price_or_volume_count: 0 },
          pending_proposals: [proposal],
          blocked_proposals: [],
          warnings: [
            'Research status is read-only and contains no secrets.',
            'No broker execution.',
          ],
        }),
      );
      return;
    }
    if (url.pathname === '/operations/scheduler-status') {
      await route.fulfill(json(schedulerSummary(schedulerJobs)));
      return;
    }
    if (url.pathname === '/scheduler/jobs/run-pending' && request.method() === 'POST') {
      calls.runPending += 1;
      const body = request.postDataJSON() as { max_jobs?: number };
      const maxJobs = Math.max(1, Math.min(body.max_jobs ?? 3, 10));
      const queued = schedulerJobs.filter((job) => job.status === 'QUEUED').slice(0, maxJobs);
      const results = queued.map((job) => {
        const completed = {
          ...job,
          status: 'COMPLETED',
          result: { status: 'ok', report: { summary: { status: 'ok' } } },
          completed_at: '2026-07-01T12:45:00Z',
          updated_at: '2026-07-01T12:45:00Z',
        };
        schedulerJobs = schedulerJobs.map((item) =>
          item.job_id === job.job_id ? completed : item,
        );
        schedulerEvents.push({
          event_id: `scheduler-event-${schedulerEvents.length + 1}`,
          job_id: String(job.job_id),
          event_type: 'JOB_COMPLETED',
          message: 'Scheduler job finished with status COMPLETED.',
          metadata: {},
          created_at: '2026-07-01T12:45:00Z',
        });
        return completed;
      });
      await route.fulfill(
        json({ status: 'ok', max_jobs: maxJobs, jobs_run: results.length, results }),
      );
      return;
    }
    if (url.pathname === '/scheduler/jobs' && request.method() === 'GET') {
      await route.fulfill(json({ jobs: schedulerJobs, limit: 100, offset: 0 }));
      return;
    }
    if (url.pathname === '/scheduler/jobs' && request.method() === 'POST') {
      calls.schedulerCreate += 1;
      calls.schedulerCreateBody = request.postDataJSON();
      const body = calls.schedulerCreateBody as {
        job_type?: string;
        payload?: Record<string, unknown>;
      };
      const job = {
        ...baseSchedulerJob,
        job_id: `scheduler-${String(schedulerJobs.length + 1).padStart(3, '0')}`,
        job_type: body.job_type ?? 'data_quality_report',
        status: 'QUEUED',
        payload: body.payload ?? {},
        created_at: '2026-07-01T12:42:00Z',
        updated_at: '2026-07-01T12:42:00Z',
      };
      schedulerJobs = [job, ...schedulerJobs];
      schedulerEvents.push({
        event_id: `scheduler-event-${schedulerEvents.length + 1}`,
        job_id: String(job.job_id),
        event_type: 'JOB_CREATED',
        message: 'Scheduler job queued.',
        metadata: {},
        created_at: '2026-07-01T12:42:00Z',
      });
      await route.fulfill(json(job));
      return;
    }
    if (url.pathname.startsWith('/scheduler/jobs/')) {
      const [, , , jobId, action] = url.pathname.split('/');
      const job = schedulerJobs.find((item) => item.job_id === jobId);
      if (action === 'events') {
        await route.fulfill(
          json({
            job_id: jobId,
            events: schedulerEvents.filter((event) => event.job_id === jobId),
            limit: 500,
            offset: 0,
          }),
        );
        return;
      }
      if (action === 'run') {
        const completed = {
          ...job,
          status: 'COMPLETED',
          result: { status: 'ok', report: { summary: { status: 'ok' } } },
          completed_at: '2026-07-01T12:46:00Z',
          updated_at: '2026-07-01T12:46:00Z',
        };
        schedulerJobs = schedulerJobs.map((item) => (item.job_id === jobId ? completed : item));
        await route.fulfill(json(completed));
        return;
      }
      if (action === 'cancel') {
        const cancelled = {
          ...job,
          status: 'CANCELLED',
          completed_at: '2026-07-01T12:46:00Z',
          updated_at: '2026-07-01T12:46:00Z',
        };
        schedulerJobs = schedulerJobs.map((item) => (item.job_id === jobId ? cancelled : item));
        await route.fulfill(json(cancelled));
        return;
      }
      await route.fulfill(json(job ?? { status: 'not_found', job_id: jobId }));
      return;
    }
    if (url.pathname === '/research/cycles' && request.method() === 'GET') {
      await route.fulfill(json({ research_cycles: [cycle], limit: 100, offset: 0 }));
      return;
    }
    if (url.pathname === '/research/cycles' && request.method() === 'POST') {
      calls.cycleCreateBody = request.postDataJSON();
      await route.fulfill(json(cycle));
      return;
    }
    if (url.pathname === '/research/cycles/cycle-001/dry-run') {
      calls.dryRun += 1;
      await route.fulfill(
        json({
          status: 'dry_run',
          research_cycle_id: 'cycle-001',
          summary: { model_activation_unchanged: true },
        }),
      );
      return;
    }
    if (url.pathname === '/research/cycles/cycle-001/run') {
      await route.fulfill(
        json({
          status: 'completed',
          research_cycle_id: 'cycle-001',
          summary: { model_activation_unchanged: true },
        }),
      );
      return;
    }
    if (url.pathname === '/research/cycles/cycle-001/artifacts') {
      await route.fulfill(
        json({
          artifacts: [
            {
              cycle_artifact_id: 'artifact-001',
              research_cycle_id: 'cycle-001',
              artifact_type: 'model_proposal',
              source_id: 'proposal-001',
              source_table: 'model_proposals',
              payload: {},
              created_at: '2026-07-01T12:15:00Z',
            },
          ],
          limit: 500,
          offset: 0,
        }),
      );
      return;
    }
    if (url.pathname === '/research/model-proposals' && request.method() === 'GET') {
      await route.fulfill(json({ model_proposals: [proposal], limit: 100, offset: 0 }));
      return;
    }
    if (url.pathname === '/research/model-proposals/proposal-001' && request.method() === 'GET') {
      await route.fulfill(json(proposal));
      return;
    }
    if (url.pathname === '/research/model-proposals/proposal-001/approve') {
      calls.approve += 1;
      proposal = {
        ...proposal,
        status: 'APPROVED_FOR_ACTIVATION',
        approved_by: 'operator',
        approved_at: '2026-07-01T12:20:00Z',
      };
      await route.fulfill(json(proposal));
      return;
    }
    if (url.pathname === '/research/model-proposals/proposal-001/reject') {
      proposal = { ...proposal, status: 'REJECTED' };
      await route.fulfill(json(proposal));
      return;
    }
    if (url.pathname === '/research/model-proposals/proposal-001/activate') {
      calls.activate += 1;
      calls.activateBody = request.postDataJSON();
      await route.fulfill(
        json({
          status: 'blocked',
          reason: 'validation_report_required',
          proposal_id: 'proposal-001',
        }),
      );
      return;
    }
    if (url.pathname === '/research/decision-ledger') {
      await route.fulfill(
        json({
          decisions: [
            {
              decision_id: 'decision-001',
              decision_type: 'PROPOSAL_APPROVED',
              research_cycle_id: 'cycle-001',
              proposal_id: 'proposal-001',
              model_version: 'challenger-v2',
              previous_model_version: 'champion-v1',
              decision_status: 'APPROVED',
              reason_codes: ['manual_operator_review'],
              evidence_refs: [{ proposal_id: 'proposal-001' }],
              actor: 'operator',
              created_at: '2026-07-01T12:20:00Z',
              metadata: {},
            },
          ],
          limit: 100,
          offset: 0,
        }),
      );
      return;
    }
    if (url.pathname.startsWith('/exports/')) {
      await route.fulfill(
        json({
          status: 'ok',
          export: {
            export_id: 'export-001',
            file_format: 'xlsx',
            rows: 1,
            created_at: '2026-07-01T12:30:00Z',
          },
        }),
      );
      return;
    }

    await route.fulfill(json({ status: 'not_found', reason: url.pathname }));
  });

  return calls;
}

test('operations page loads research status', async ({ page }) => {
  await installGovernanceMocks(page);
  await page.goto('/operations');
  await expect(page.getByRole('heading', { name: 'Operations' })).toBeVisible();
  await expect(page.getByText('champion-v1').first()).toBeVisible();
  await expect(page.getByRole('link', { name: /cycle-001/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /queued/ })).toBeVisible();
});

test('research cycles create form normalizes APPL and dry-run calls backend', async ({ page }) => {
  const calls = await installGovernanceMocks(page);
  await page.goto('/research/cycles');
  await expect(page.getByRole('heading', { name: 'Research cycles' })).toBeVisible();

  await page.locator('label').filter({ hasText: 'Symbols' }).locator('input').fill('APPL,SPY');
  await page.getByRole('button', { name: 'Create cycle' }).click();
  await expect.poll(() => calls.requests.join(' | ')).toContain('POST /research/cycles');
  await expect.poll(() => calls.cycleCreateBody).not.toBeNull();
  expect((calls.cycleCreateBody as { symbols?: string[] }).symbols).toEqual(['AAPL', 'SPY']);

  await page.getByRole('button', { name: 'Dry-run' }).first().click();
  await expect.poll(() => calls.dryRun).toBe(1);
});

test('proposal approval does not activate and activation requires explicit confirmation', async ({
  page,
}) => {
  const calls = await installGovernanceMocks(page);
  await page.goto('/research/proposals/proposal-001');
  await expect(page.getByRole('heading', { name: 'Model proposal' })).toBeVisible();

  await expect(
    page.getByRole('button', { name: 'Activate approved scanner model' }),
  ).toBeDisabled();
  await page.getByRole('button', { name: 'Approve proposal' }).click();
  await expect.poll(() => calls.approve).toBe(1);
  expect(calls.activate).toBe(0);

  await expect(
    page.getByRole('button', { name: 'Activate approved scanner model' }),
  ).toBeDisabled();
  await page.getByLabel('Activation confirmation phrase').fill('ACTIVATE SCANNER MODEL');
  await page.getByLabel('I understand this is a manual scanner model update only.').check();
  await expect(page.getByRole('button', { name: 'Activate approved scanner model' })).toBeEnabled();
  await page.getByRole('button', { name: 'Activate approved scanner model' }).click();
  await expect.poll(() => calls.activate).toBe(1);
  expect(
    (calls.activateBody as { confirm_manual_activation?: boolean }).confirm_manual_activation,
  ).toBe(true);
});

test('decision ledger loads and filters', async ({ page }) => {
  await installGovernanceMocks(page);
  await page.goto('/research/decision-ledger');
  await expect(page.getByRole('heading', { name: 'Decision ledger' })).toBeVisible();
  await page.getByLabel('Proposal ID').fill('proposal-001');
  await page.getByRole('button', { name: 'Apply filters' }).click();
  await expect(page.getByText('PROPOSAL_APPROVED')).toBeVisible();
});

test('scheduler page creates and runs bounded jobs safely', async ({ page }) => {
  const calls = await installGovernanceMocks(page);
  await page.goto('/operations/scheduler');
  await expect(page.getByRole('heading', { name: 'Scheduler' })).toBeVisible();
  await expect(page.getByLabel('Job Type')).toHaveValue('data_quality_report');

  await page.locator('label').filter({ hasText: 'Symbols' }).locator('input').fill('APPL,SPY');
  await page.getByRole('button', { name: 'Create job' }).click();
  await expect.poll(() => calls.schedulerCreate).toBe(1);
  expect(
    ((calls.schedulerCreateBody as { payload?: { symbols?: string[] } }).payload ?? {}).symbols,
  ).toEqual(['AAPL', 'SPY']);

  await page.getByRole('button', { name: 'Run pending' }).click();
  await expect.poll(() => calls.runPending).toBe(1);
  await expect(page.getByText(/Run pending completed/)).toBeVisible();
});

test('scheduler detail shows events and safe queued controls', async ({ page }) => {
  await installGovernanceMocks(page);
  await page.goto('/operations/scheduler/scheduler-001');
  await expect(page.getByRole('heading', { name: 'Scheduler job' })).toBeVisible();
  await expect(page.getByText('JOB_CREATED')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Run job' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Cancel job' })).toBeEnabled();
});

test('governance pages do not expose secrets or execution controls', async ({ page }) => {
  await installGovernanceMocks(page);
  for (const path of [
    '/operations',
    '/operations/scheduler',
    '/operations/scheduler/scheduler-001',
    '/research/cycles',
    '/research/proposals',
    '/research/decision-ledger',
    '/research/status',
  ]) {
    await page.goto(path);
    await expect(page.locator('body')).not.toContainText('FMP_API_KEY');
    await expect(page.locator('body')).not.toContainText('DATABASE_URL');
    const controls = [
      ...(await page.getByRole('button').allInnerTexts()),
      ...(await page.getByRole('link').allInnerTexts()),
    ].join(' ');
    expect(controls).not.toMatch(/\b(buy|sell|order)\b/i);
  }
});
