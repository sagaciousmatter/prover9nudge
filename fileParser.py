"""For reading and parsing Prover9 input and output files."""

import os
import sys
import string
import gzip
import hashlib
import random
import collections
import globalConfig as gc
import sqlInterface
import textUtilities
import clause as ladrClause
import graphUtilities

def allWhiteSpace(s):
    sentinal = True
    for c in s:
        if not c in string.whitespace: sentinal = False
    return sentinal

def isOutputFile(fileName):
    """Returns True if it's an output file with a proof."""
    if 'gz' == fileName[-2:]:
        f = gzip.open(fileName, 'r')
    else:
        f = open(fileName, 'r')
    sentinal = False
    for line in f:
        if gc.PROOF_START in line:
            #print '++++++++++++++++++++++++'
            sentinal = True
    f.close()
    #print fileName, sentinal
    return sentinal

def isInputFile(fileName):
    """Returns True if it's an input file (i.e. has at least
       one list we typically find in an input file)."""
    f = open(fileName, 'r')
    sentinal = False
    search_string_sentinal = False
    for line in f:
        if gc.SOS_START in line: sentinal = True
        if gc.USABLE_START in line: sentinal = True
        if gc.GOALS_START in line: sentinal = True
        if gc.ASSUMPTIONS_START in line: sentinal = True
        if gc.SEARCH_STRING in line: search_string_sentinal = True
    f.close()
    return (sentinal and not search_string_sentinal)

def determineFile(fileName):
    """Tests whether it's got proofs. If it does, call readOutputFile;
       if it doesn't, call readInputFile."""
    out = None
    if isOutputFile(fileName):
        out = readOutputFile(fileName)
    if isInputFile(fileName):
       out = readInputFile(fileName)
    return out

def readOutputFile(fileName):
    """Given the name of a file containing proofs, returns
       a list of lists of NonUnitClauses."""
    if 'gz' == fileName[-2:]:
        f = gzip.open(fileName)
    else:
        f = open(fileName, 'r')
    inProof = False
    proofs = []
    for line in f:
        if '&' in line: continue
        if '<->' in line: continue
        if '->' in line: continue
        if allWhiteSpace(line): continue
        if '(all' in line: continue
        if '(exists' in line: continue
        if gc.PROOF_START in line:
            inProof = True
            oneProof = []
            continue
        if gc.PROOF_END in line:
            inProof = False
            proofs.append(oneProof)
        if inProof and '.' in line:
            raw_clause = extractClauseFromLine(line) # here
            if len(raw_clause) <= 5: continue
            one_clause = ladrClause.Clause(raw_clause)
            oneProof.append(one_clause)
    return proofs

def extractClauseFromLine(line):
    line = line.split('#')
    if len(line) > 1:
        line = line[0]
    else:
        line = ''.join(line)
    line = line.split(gc.COMMENT_MARKER)
    if len(line) > 1:
        line = line[0]
    else:
        line = ''.join(line)
    if '[' in line and ']' in line:
        line = line[:line.index('[')] + line[line.index(']')+1:]
    line = line.split(' ')
    line = [i for i in line if not textUtilities.allDigits(i)]
    line = ' '.join(line)
    line = ''.join([c for c in line if not c == gc.END_OF_STATEMENT])
    line = line.strip()
    line = line + gc.END_OF_STATEMENT
    if len(line) > 3 and not r'$' in line:
        return line
    else:
        return ''

s1 = '2 P(j(j(x,y),j(j(y,z),j(x,z)))) # label(non_clause) # label(goal).  [goal].'
s1 = '5 -P(j(x,y)) | -P(x) | P(y).  [assumption].'
print extractClauseFromLine(s1)


def readFile(fileName):
    if 'gz' == fileName[-2:]:
        f = gzip.open(fileName)
    else:
        f = open(fileName)
    out = f.read()
    f.close()
    return out

def readInputFile(fileName):
    """Given the name of an input file, returns a list of 
       NonUnitClauses, including labels for which list the
       clauses were in."""
    f = open(fileName, 'r')
    allClauses = []
    inSos = False
    inUsable = False
    inGoals = False
    inAssumptions = False
    for s in f:
        #print s
        line = textUtilities.stripWhitespace(s)
        # find comments and strip them out
        if gc.COMMENT_MARKER in line:
            commentStart = line.index(gc.COMMENT_MARKER)
            line = line[:commentStart]
        # split the line with each delimiter
        line = line.split(gc.END_OF_STATEMENT)
        for statement in line:
            if 'end_of_list' in statement: continue
            if textUtilities.allWhitespace(statement): continue
            print 'sending:', statement
            statement = extractClauseFromLine(statement)
            print 'returning:', statement
            if len(statement) < 5: continue
            if gc.ASSUMPTIONS in statement: 
                inAssumptions = True
                continue
            if gc.SOS_START in statement: 
                inSos = True
                continue
            if gc.USABLE_START in statement:
                inUsable = True
                continue
            if gc.GOALS_START in statement:
                inGoals = True
                continue
            if gc.END_OF_LIST in statement:
                inAssumptions = False
                inSos = False
                inUsable = False
                inGoals = False
                continue
            if not(inSos or inUsable or inGoals):
                continue
            clause = ladrClause.Clause(statement)
            allClauses.append(clause)
    f.close()
    return allClauses


print readOutputFile('./test_files/prop.out')
print readInputFile('./test_files/prop.in')
exit()

def parseProofFilesInDirectory(directory):
    fileList = [directory + '/' + i for i in os.listdir(directory)]
    for fileName in fileList:
        #print fileName
        if isOutputFile(fileName):
            #print '--->', fileName
            parsed = readOutputFile(fileName)
            for one_list in parsed:
                for unit in one_list:
                    unit.prettyPrint()

def makeGraphFromDirectory(directory):
    #print 'source,target'
    d = collections.defaultdict(list)
    fileList = [directory + '/' + i for i in os.listdir(directory) if 'GRP' in i]
    counter = 0
    for fileName in fileList:#random.sample(fileList, 1750):
        #print fileName
        related = []
        if isOutputFile(fileName):
            print '--->', fileName, counter
            counter += 1
            parsed = readOutputFile(fileName)
            for proof in parsed:
                for clause1 in proof:
                    for clause2 in proof:
                        f1 = [[i for i in unit.canonicalized] for unit in clause1.units]
                        f2 = [[i for i in unit.canonicalized] for unit in clause2.units]
                        if len(f1) < 4 or len(f2) < 4: continue
                        s1 = ''.join([''.join([i for i in unit.canonicalized]) for unit in clause1.units])
                        s2 = ''.join([''.join([i for i in unit.canonicalized]) for unit in clause2.units])
                        #if s1 <= s2: continue
                        h1 = hashlib.sha224(s1).hexdigest()             
                        h2 = hashlib.sha224(s2).hexdigest()
                        d[h1].append(h2)
                        d[h2].append(h1)
                        #print '"' + h1 + '","' + h2 + '"'
    d = dict(d)
    return d


def directoryToSQL(directory):
    #print 'source,target'
    d = collections.defaultdict(list)
    fileList = [directory + '/' + i for i in os.listdir(directory)]
    counter = 0
    for fileName in random.sample(fileList, 1600):
        #print fileName
        related = []
        if isOutputFile(fileName):
            print '--->', fileName, counter
            counter += 1
            parsed = readOutputFile(fileName)
            rawFile = readFile(fileName)
            #print rawFile
            proofHash = hashlib.sha224(rawFile).hexdigest()             
            print proofHash
            sqlInterface.insertValues(gc.MYSQL_PROOFS_TABLE,
                           [gc.MYSQL_PROOF_HASH, gc.MYSQL_RAW_PROOF_COLUMN, gc.MYSQL_PARSED_PROOF_COLUMN], [proofHash, rawFile, parsed],
                           [gc.MYSQL_RAW_PROOF_COLUMN, gc.MYSQL_PARSED_PROOF_COLUMN])


directoryToSQL('./ladr_with_proofs')
