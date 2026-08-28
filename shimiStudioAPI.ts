import { base44, createClientFromRequest } from '@base44/sdk';

export default async function (req: Request): Promise<Response> {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
  };

  // Handle CORS preflight OPTIONS request
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  const jsonResponse = (data: any, status = 200) => {
    return new Response(JSON.stringify(data), {
      status,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders,
      },
    });
  };

  try {
    // Initialize base44 client (use request context if available, otherwise global base44)
    const client = typeof createClientFromRequest === 'function' ? createClientFromRequest(req) : base44;

    let body: any = {};
    if (req.method === 'POST' || req.method === 'PUT') {
      body = await req.json().catch(() => ({}));
    } else {
      const url = new URL(req.url);
      url.searchParams.forEach((val, key) => {
        body[key] = val;
      });
    }

    const { action, ...params } = body;

    switch (action) {
      case 'get_pending':
        return await handleGetPending(client, params, jsonResponse);
      case 'claim':
        return await handleClaim(client, params, jsonResponse);
      case 'update_progress':
        return await handleUpdateProgress(client, params, jsonResponse);
      case 'complete':
        return await handleComplete(client, params, jsonResponse);
      case 'fail':
        return await handleFail(client, params, jsonResponse);
      case 'get_job':
        return await handleGetJob(client, params, jsonResponse);
      case 'create':
        return await handleCreate(client, params, jsonResponse);
      case 'create_batch':
        return await handleCreateBatch(client, params, jsonResponse);
      case 'upload':
        return await handleUpload(client, params, jsonResponse);
      case 'stats':
        return await handleStats(client, params, jsonResponse);

      // Additional backward-compatible actions
      case 'update':
        return await handleUpdateGeneric(client, params, jsonResponse);
      case 'status':
        return await handleGetJob(client, params, jsonResponse);
      case 'list':
        return await handleListJobs(client, params, jsonResponse);
      case 'cancel':
        return await handleCancelJob(client, params, jsonResponse);

      default:
        return jsonResponse({ error: `Unknown action: ${action}` }, 400);
    }
  } catch (err: any) {
    console.error('ShimiStudio API Error:', err);
    return jsonResponse(
      {
        error: err.message || 'Internal Server Error',
        stack: err.stack,
      },
      500
    );
  }
}

// ─── ACTION HANDLERS ───

async function handleGetPending(client: any, params: any, json: Function) {
  const limit = params.limit ? parseInt(params.limit, 10) : 5;
  const jobs = await client.entities.RenderJob.list({
    filter: { status: 'pending' },
    sort: '-priority',
    limit: limit,
  });

  return json({
    success: true,
    count: jobs.length,
    jobs: jobs.map(formatJobResponse),
  });
}

async function handleClaim(client: any, params: any, json: Function) {
  let jobId = params.job_id || params.id;
  const workerId = params.worker_id || 'worker-default';

  if (!jobId) {
    const pending = await client.entities.RenderJob.list({
      filter: { status: 'pending' },
      sort: '-priority',
      limit: 1,
    });

    if (!pending || pending.length === 0) {
      return json({ success: false, message: 'No pending jobs available' }, 404);
    }
    jobId = pending[0].id;
  }

  const updated = await client.entities.RenderJob.update(jobId, {
    worker_id: workerId,
    status: 'processing',
    started_at: new Date().toISOString(),
  });

  return json({
    success: true,
    job_id: jobId,
    job: formatJobResponse(updated),
  });
}

async function handleUpdateProgress(client: any, params: any, json: Function) {
  const jobId = params.job_id || params.id;
  if (!jobId) {
    return json({ error: 'job_id is required' }, 400);
  }

  const progress = params.progress !== undefined ? Number(params.progress) : 0;
  const updateData: any = { progress };

  if (params.status) updateData.status = params.status;
  if (params.step !== undefined) updateData.step = params.step;
  if (params.total_steps !== undefined) updateData.total_steps = params.total_steps;
  if (params.message) updateData.message = params.message;

  const updated = await client.entities.RenderJob.update(jobId, updateData);

  return json({
    success: true,
    job_id: jobId,
    job: formatJobResponse(updated),
  });
}

async function handleComplete(client: any, params: any, json: Function) {
  const jobId = params.job_id || params.id;
  if (!jobId) {
    return json({ error: 'job_id is required' }, 400);
  }

  const updated = await client.entities.RenderJob.update(jobId, {
    status: 'completed',
    output_url: params.output_url || '',
    completed_at: new Date().toISOString(),
    progress: 100,
    result_metadata: params.result_metadata || params.metadata || {},
  });

  return json({
    success: true,
    job_id: jobId,
    job: formatJobResponse(updated),
  });
}

async function handleFail(client: any, params: any, json: Function) {
  const jobId = params.job_id || params.id;
  if (!jobId) {
    return json({ error: 'job_id is required' }, 400);
  }

  const errorMsg = params.error_message || params.error || 'Job processing failed';
  const updated = await client.entities.RenderJob.update(jobId, {
    status: 'failed',
    error_message: errorMsg,
    completed_at: new Date().toISOString(),
  });

  return json({
    success: true,
    job_id: jobId,
    job: formatJobResponse(updated),
  });
}

async function handleGetJob(client: any, params: any, json: Function) {
  const jobId = params.job_id || params.id;
  if (!jobId) {
    return json({ error: 'job_id is required' }, 400);
  }

  const job = await client.entities.RenderJob.get(jobId);
  if (!job) {
    return json({ error: `Job with ID ${jobId} not found` }, 404);
  }

  return json({
    success: true,
    job: formatJobResponse(job),
  });
}

async function handleCreate(client: any, params: any, json: Function) {
  const {
    job_type,
    prompt,
    negative_prompt,
    reference_image,
    face_images,
    face_swap_target,
    voice_text,
    camera_frames,
    parameters,
    workflow_id,
    client_id,
    priority,
    style,
    mood,
    character,
    created_by_name,
  } = params;

  const validTypes = [
    'text_to_image',
    'image_to_video',
    'text_to_video',
    'face_id',
    'face_swap',
    'tts_lipsync',
    'full_pipeline',
    'camera_capture',
    'batch_generation',
  ];

  const type = validTypes.includes(job_type) ? job_type : 'text_to_image';

  const newJob = await client.entities.RenderJob.create({
    job_type: type,
    prompt: prompt || '',
    negative_prompt: negative_prompt || '',
    reference_image: reference_image || '',
    face_images: face_images || [],
    face_swap_target: face_swap_target || '',
    voice_text: voice_text || '',
    camera_frames: camera_frames || '',
    parameters: parameters || {},
    workflow_id: workflow_id || '',
    client_id: client_id || '',
    priority: priority !== undefined ? Number(priority) : 5,
    style: style || '',
    mood: mood || '',
    character: character || '',
    created_by_name: created_by_name || 'ShimiStudio User',
    status: 'pending',
    progress: 0,
    created_at: new Date().toISOString(),
  });

  return json({
    success: true,
    job_id: newJob.id,
    message: `Job ${type} created successfully`,
    job: formatJobResponse(newJob),
  });
}

async function handleCreateBatch(client: any, params: any, json: Function) {
  const { jobs } = params;
  if (!Array.isArray(jobs) || jobs.length === 0) {
    return json({ error: 'jobs array required' }, 400);
  }

  const createdJobs = [];
  for (const item of jobs) {
    const created = await client.entities.RenderJob.create({
      job_type: item.job_type || 'text_to_image',
      prompt: item.prompt || '',
      negative_prompt: item.negative_prompt || '',
      reference_image: item.reference_image || '',
      face_images: item.face_images || [],
      face_swap_target: item.face_swap_target || '',
      voice_text: item.voice_text || '',
      parameters: item.parameters || {},
      priority: item.priority !== undefined ? Number(item.priority) : 5,
      style: item.style || '',
      mood: item.mood || '',
      character: item.character || '',
      status: 'pending',
      progress: 0,
      created_at: new Date().toISOString(),
    });
    createdJobs.push(formatJobResponse(created));
  }

  return json({
    success: true,
    count: createdJobs.length,
    jobs: createdJobs,
  });
}

async function handleUpload(client: any, params: any, json: Function) {
  const { base64_data, filename, mime_type } = params;
  if (!base64_data) {
    return json({ error: 'base64_data is required' }, 400);
  }

  const name = filename || `upload_${Date.now()}.png`;
  const type = mime_type || 'image/png';

  const fileUrl = base64_data.startsWith('data:')
    ? base64_data
    : `data:${type};base64,${base64_data}`;

  return json({
    success: true,
    filename: name,
    mime_type: type,
    output_url: fileUrl,
    url: fileUrl,
  });
}

async function handleStats(client: any, params: any, json: Function) {
  const allJobs = await client.entities.RenderJob.list({ limit: 1000 });
  const todayStr = new Date().toISOString().split('T')[0];

  let pending = 0;
  let processing = 0;
  let completed = 0;
  let completed_today = 0;
  let failed = 0;

  for (const j of allJobs) {
    const s = j.status || (j.data && j.data.status);
    const compAt = j.completed_at || (j.data && j.data.completed_at);

    if (s === 'pending') pending++;
    else if (s === 'processing' || s === 'claimed') processing++;
    else if (s === 'completed') {
      completed++;
      if (compAt && compAt.startsWith(todayStr)) {
        completed_today++;
      }
    } else if (s === 'failed') failed++;
  }

  return json({
    success: true,
    stats: {
      total: allJobs.length,
      pending,
      processing,
      completed,
      completed_today,
      failed,
    },
  });
}

async function handleUpdateGeneric(client: any, params: any, json: Function) {
  const jobId = params.job_id || params.id;
  if (!jobId) return json({ error: 'job_id is required' }, 400);

  const updateObj: any = {};
  if (params.status) updateObj.status = params.status;
  if (params.progress !== undefined) updateObj.progress = Number(params.progress);
  if (params.output_url) updateObj.output_url = params.output_url;
  if (params.error_message) updateObj.error_message = params.error_message;
  if (params.status === 'completed' || params.status === 'failed') {
    updateObj.completed_at = new Date().toISOString();
  }

  const updated = await client.entities.RenderJob.update(jobId, updateObj);
  return json({ success: true, job_id: jobId, job: formatJobResponse(updated) });
}

async function handleListJobs(client: any, params: any, json: Function) {
  const filter: any = {};
  if (params.status_filter || params.status) filter.status = params.status_filter || params.status;
  if (params.job_type_filter || params.job_type) filter.job_type = params.job_type_filter || params.job_type;

  const limit = params.limit ? parseInt(params.limit, 10) : 20;

  const jobs = await client.entities.RenderJob.list({
    filter: Object.keys(filter).length > 0 ? filter : undefined,
    sort: '-created_date',
    limit,
  });

  return json({
    success: true,
    count: jobs.length,
    jobs: jobs.map(formatJobResponse),
  });
}

async function handleCancelJob(client: any, params: any, json: Function) {
  const jobId = params.job_id || params.id;
  if (!jobId) return json({ error: 'job_id is required' }, 400);

  const updated = await client.entities.RenderJob.update(jobId, {
    status: 'failed',
    error_message: 'Cancelled by user request',
    completed_at: new Date().toISOString(),
  });

  return json({ success: true, job_id: jobId, message: 'Job cancelled', job: formatJobResponse(updated) });
}

function formatJobResponse(j: any) {
  if (!j) return null;
  const data = j.data || {};
  return {
    id: j.id,
    job_type: j.job_type || data.job_type,
    status: j.status || data.status,
    progress: j.progress !== undefined ? j.progress : data.progress,
    prompt: j.prompt || data.prompt || '',
    negative_prompt: j.negative_prompt || data.negative_prompt || '',
    reference_image: j.reference_image || data.reference_image || '',
    face_images: j.face_images || data.face_images || [],
    face_swap_target: j.face_swap_target || data.face_swap_target || '',
    voice_text: j.voice_text || data.voice_text || '',
    camera_frames: j.camera_frames || data.camera_frames || '',
    parameters: j.parameters || data.parameters || {},
    priority: j.priority !== undefined ? j.priority : data.priority,
    worker_id: j.worker_id || data.worker_id,
    output_url: j.output_url || data.output_url,
    error_message: j.error_message || data.error_message,
    created_at: j.created_at || j.created_date || data.created_at,
    started_at: j.started_at || data.started_at,
    completed_at: j.completed_at || data.completed_at,
  };
}
