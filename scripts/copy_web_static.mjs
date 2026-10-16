import {cp,mkdir} from 'node:fs/promises';
await mkdir('.next/standalone/apps/web/.next',{recursive:true});
await cp('.next/static','.next/standalone/apps/web/.next/static',{recursive:true});
