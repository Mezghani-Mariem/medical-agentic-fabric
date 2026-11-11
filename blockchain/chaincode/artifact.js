'use strict';
const { Contract } = require('fabric-contract-api');

const ALLOWED_TYPES = new Set([
  'raw_ecg','raw_report','processed','features',
  'prediction','validation','explanation','final'
]);

class ArtifactContract extends Contract {
  async createArtifact(ctx, recordJson) {
    const record = JSON.parse(recordJson);
    const required = [
      'artifact_id','case_id','type','sha256','created_at',
      'version','parent_id','storage_ref','created_by'
    ];
    for (const k of required) {
      if (!(k in record)) throw new Error(`champ manquant: ${k}`);
    }
    if (!ALLOWED_TYPES.has(record.type)) {
      throw new Error(`type invalide: ${record.type}`);
    }
    if (!/^[0-9a-f]{64}$/.test(record.sha256)) {
      throw new Error('sha256 invalide');
    }
    const existing = await ctx.stub.getState(record.artifact_id);
    if (existing && existing.length > 0) {
      throw new Error(`artifact_id déjà enregistré: ${record.artifact_id}`);
    }
    await ctx.stub.putState(record.artifact_id, Buffer.from(JSON.stringify(record)));
    return ctx.stub.getTxID();
  }

  async readArtifact(ctx, artifactId) {
    const data = await ctx.stub.getState(artifactId);
    if (!data || data.length === 0) {
      throw new Error(`artifact_id inconnu: ${artifactId}`);
    }
    return data.toString();
  }
}

module.exports = ArtifactContract;
module.exports.contracts = [ArtifactContract];